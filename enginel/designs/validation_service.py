"""
Validation service for Enginel data validation system.

Provides centralized validation logic for:
- Applying validation rules to models
- Running custom validators
- Recording validation results
- Generating validation reports
- Managing validation workflows
"""
import re
import uuid
import importlib
from typing import Dict, List, Any, Optional, Tuple
from django.core.exceptions import ValidationError
from django.db import transaction, models
from django.utils import timezone
from designs.models import ValidationRule, ValidationResult
from designs.validators import *


class ValidationService:
    """
    Central service for data validation.
    
    Handles:
    - Rule application
    - Result recording
    - Batch validation
    - Validation reporting
    """
    
    def __init__(self):
        self.validators = {
            'REGEX': self._validate_regex,
            'RANGE': self._validate_range,
            'LENGTH': self._validate_length,
            'FORMAT': self._validate_format,
            'CUSTOM': self._validate_custom,
            'FILE_TYPE': self._validate_file_type,
            'FILE_SIZE': self._validate_file_size,
            'UNIQUENESS': self._validate_uniqueness,
            'RELATIONSHIP': self._validate_relationship,
            'BUSINESS_RULE': self._validate_business_rule,
        }
    
    def validate_model_instance(
        self,
        instance,
        operation='create',
        user=None,
        organization=None
    ) -> Tuple[bool, List[ValidationResult]]:
        """
        Validate a model instance against all applicable rules.
        
        Args:
            instance: Model instance to validate
            operation: 'create' or 'update'
            user: User performing the operation
            organization: Organization context
        
        Returns:
            Tuple of (is_valid, list of validation results)
        """
        model_name = instance.__class__.__name__
        
        # Get applicable rules
        rules = self._get_applicable_rules(
            model_name=model_name,
            operation=operation,
            organization=organization
        )
        
        results = []
        is_valid = True
        
        for rule in rules:
            result = self._apply_rule(
                rule=rule,
                instance=instance,
                user=user
            )
            results.append(result)
            
            if result.status == 'FAILED' and rule.severity in ['ERROR', 'CRITICAL']:
                is_valid = False
        
        return is_valid, results
    
    def validate_field_value(
        self,
        model_name: str,
        field_name: str,
        value: Any,
        user=None,
        organization=None
    ) -> Tuple[bool, List[ValidationResult]]:
        """
        Validate a specific field value.
        
        Args:
            model_name: Name of the model
            field_name: Name of the field
            value: Value to validate
            user: User performing validation
            organization: Organization context
        
        Returns:
            Tuple of (is_valid, list of validation results)
        """
        rules = ValidationRule.objects.filter(
            target_model=model_name,
            target_field=field_name,
            is_active=True
        )
        
        if organization:
            rules = rules.filter(
                models.Q(organization=organization) | models.Q(organization__isnull=True)
            )
        
        results = []
        is_valid = True
        
        for rule in rules:
            try:
                self._run_validator(rule, value)
                status = 'PASSED'
                error_msg = ''
            except ValidationError as e:
                status = 'FAILED'
                error_msg = str(e)
                if rule.severity in ['ERROR', 'CRITICAL']:
                    is_valid = False
                rule.increment_failures()
            
            rule.increment_checks()
            
            # Create result record
            result = ValidationResult.objects.create(
                rule=rule,
                target_model=model_name,
                target_id=uuid.uuid4(),  # Temporary ID for field validation
                target_field=field_name,
                status=status,
                error_message=error_msg,
                validated_by=user,
                details={
                    'value': str(value),
                    'rule_type': rule.rule_type,
                    'severity': rule.severity
                }
            )
            results.append(result)
        
        return is_valid, results
    
    def validate_batch(
        self,
        instances: List[Any],
        operation='create',
        user=None,
        organization=None
    ) -> Dict[str, Any]:
        """
        Validate multiple instances in batch.
        
        Args:
            instances: List of model instances
            operation: 'create' or 'update'
            user: User performing operation
            organization: Organization context
        
        Returns:
            Dictionary with validation summary
        """
        total = len(instances)
        valid_count = 0
        invalid_count = 0
        all_results = []
        
        for instance in instances:
            is_valid, results = self.validate_model_instance(
                instance=instance,
                operation=operation,
                user=user,
                organization=organization
            )
            
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
            
            all_results.extend(results)
        
        return {
            'total': total,
            'valid': valid_count,
            'invalid': invalid_count,
            'results': all_results,
            'summary': self._generate_summary(all_results)
        }
    
    def get_validation_report(
        self,
        model_name: str = None,
        start_date=None,
        end_date=None,
        organization=None
    ) -> Dict[str, Any]:
        """
        Generate validation report.
        
        Args:
            model_name: Filter by model name
            start_date: Filter start date
            end_date: Filter end date
            organization: Filter by organization
        
        Returns:
            Validation statistics and report
        """
        from django.db.models import Count, Q
        
        results = ValidationResult.objects.all()
        
        if model_name:
            results = results.filter(target_model=model_name)
        
        if start_date:
            results = results.filter(validated_at__gte=start_date)
        
        if end_date:
            results = results.filter(validated_at__lte=end_date)
        
        if organization:
            results = results.filter(rule__organization=organization)
        
        # Aggregate statistics
        stats = results.aggregate(
            total=Count('id'),
            passed=Count('id', filter=Q(status='PASSED')),
            failed=Count('id', filter=Q(status='FAILED')),
            blocked=Count('id', filter=Q(was_blocked=True)),
            overridden=Count('id', filter=Q(was_overridden=True))
        )
        
        # By severity
        by_severity = {}
        for result in results:
            severity = result.rule.severity
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # By rule type
        by_type = {}
        for result in results:
            rule_type = result.rule.rule_type
            by_type[rule_type] = by_type.get(rule_type, 0) + 1
        
        # Top failing rules
        from django.db.models import Count
        top_failing = (
            ValidationResult.objects.filter(status='FAILED')
            .values('rule__name', 'rule__id')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        
        return {
            'period': {
                'start': start_date,
                'end': end_date
            },
            'stats': stats,
            'by_severity': by_severity,
            'by_type': by_type,
            'top_failing_rules': list(top_failing),
            'pass_rate': round((stats['passed'] / stats['total'] * 100), 2) if stats['total'] > 0 else 0
        }
    
    # ========================================================================
    # PRIVATE METHODS - Rule Application
    # ========================================================================
    
    def _get_applicable_rules(
        self,
        model_name: str,
        operation: str,
        organization=None
    ) -> List[ValidationRule]:
        """Get rules applicable to this validation context."""
        from django.db.models import Q
        
        rules = ValidationRule.objects.filter(
            Q(target_model=model_name) | Q(target_model='*'),
            is_active=True
        )
        
        # Filter by operation
        if operation == 'create':
            rules = rules.filter(apply_on_create=True)
        elif operation == 'update':
            rules = rules.filter(apply_on_update=True)
        
        # Filter by organization
        if organization:
            rules = rules.filter(
                Q(organization=organization) | Q(organization__isnull=True)
            )
        
        return rules.order_by('severity', 'name')
    
    def _apply_rule(
        self,
        rule: ValidationRule,
        instance: Any,
        user=None
    ) -> ValidationResult:
        """Apply a single validation rule to an instance."""
        try:
            # Check conditions
            if not self._check_conditions(rule, instance):
                return ValidationResult.objects.create(
                    rule=rule,
                    target_model=instance.__class__.__name__,
                    target_id=instance.id if hasattr(instance, 'id') else uuid.uuid4(),
                    target_field=rule.target_field,
                    status='SKIPPED',
                    validated_by=user,
                    details={'reason': 'Conditions not met'}
                )
            
            # Get field value if field-specific rule
            if rule.target_field:
                value = getattr(instance, rule.target_field, None)
            else:
                value = instance
            
            # Run validator
            self._run_validator(rule, value)
            
            # Validation passed
            rule.increment_checks()
            
            return ValidationResult.objects.create(
                rule=rule,
                target_model=instance.__class__.__name__,
                target_id=instance.id if hasattr(instance, 'id') else uuid.uuid4(),
                target_field=rule.target_field,
                status='PASSED',
                validated_by=user,
                details={
                    'rule_type': rule.rule_type,
                    'severity': rule.severity
                }
            )
        
        except ValidationError as e:
            # Validation failed
            rule.increment_checks()
            rule.increment_failures()
            
            return ValidationResult.objects.create(
                rule=rule,
                target_model=instance.__class__.__name__,
                target_id=instance.id if hasattr(instance, 'id') else uuid.uuid4(),
                target_field=rule.target_field,
                status='FAILED',
                error_message=str(e),
                validated_by=user,
                was_blocked=(rule.severity in ['ERROR', 'CRITICAL']),
                details={
                    'rule_type': rule.rule_type,
                    'severity': rule.severity,
                    'config': rule.rule_config
                }
            )
        
        except Exception as e:
            # Unexpected error during validation
            return ValidationResult.objects.create(
                rule=rule,
                target_model=instance.__class__.__name__,
                target_id=instance.id if hasattr(instance, 'id') else uuid.uuid4(),
                target_field=rule.target_field,
                status='ERROR',
                error_message=f'Validation error: {str(e)}',
                validated_by=user,
                details={'exception': str(type(e).__name__)}
            )
    
    def _run_validator(self, rule: ValidationRule, value: Any):
        """Run the appropriate validator based on rule type."""
        validator_func = self.validators.get(rule.rule_type)
        
        if not validator_func:
            raise ValidationError(f'Unknown rule type: {rule.rule_type}')
        
        validator_func(rule, value)
    
    def _check_conditions(self, rule: ValidationRule, instance: Any) -> bool:
        """Check if rule conditions are met."""
        if not rule.conditions:
            return True
        
        try:
            # Simple condition checking
            for field, expected_value in rule.conditions.items():
                actual_value = getattr(instance, field, None)
                if actual_value != expected_value:
                    return False
            return True
        except:
            return True
    
    # ========================================================================
    # PRIVATE METHODS - Validators
    # ========================================================================
    
    def _validate_regex(self, rule: ValidationRule, value: Any):
        """Validate using regex pattern."""
        pattern = rule.rule_config.get('pattern')
        if not pattern:
            raise ValidationError('Regex pattern not configured')
        
        if value and not re.match(pattern, str(value)):
            raise ValidationError(rule.error_message)
    
    def _validate_range(self, rule: ValidationRule, value: Any):
        """Validate numeric range."""
        min_val = rule.rule_config.get('min')
        max_val = rule.rule_config.get('max')
        
        if value is None:
            return
        
        try:
            num_val = float(value)
            
            if min_val is not None and num_val < min_val:
                raise ValidationError(rule.error_message)
            
            if max_val is not None and num_val > max_val:
                raise ValidationError(rule.error_message)
        except (TypeError, ValueError):
            raise ValidationError('Value must be numeric')
    
    def _validate_length(self, rule: ValidationRule, value: Any):
        """Validate string/list length."""
        min_len = rule.rule_config.get('min')
        max_len = rule.rule_config.get('max')
        
        if value is None:
            return
        
        length = len(value)
        
        if min_len is not None and length < min_len:
            raise ValidationError(rule.error_message)
        
        if max_len is not None and length > max_len:
            raise ValidationError(rule.error_message)
    
    def _validate_format(self, rule: ValidationRule, value: Any):
        """Validate specific format (email, url, phone, etc.)."""
        format_type = rule.rule_config.get('type')
        
        if not value:
            return
        
        if format_type == 'email':
            from django.core.validators import EmailValidator
            EmailValidator()(value)
        
        elif format_type == 'url':
            from django.core.validators import URLValidator
            URLValidator()(value)
        
        elif format_type == 'phone':
            phone_pattern = r'^\+?1?\d{9,15}$'
            if not re.match(phone_pattern, str(value).replace('-', '').replace(' ', '')):
                raise ValidationError(rule.error_message)
        
        elif format_type == 'date':
            from datetime import datetime
            try:
                datetime.fromisoformat(str(value))
            except:
                raise ValidationError(rule.error_message)
        
        else:
            raise ValidationError(f'Unknown format type: {format_type}')
    
    def _validate_custom(self, rule: ValidationRule, value: Any):
        """Validate using custom Python expression."""
        expression = rule.rule_config.get('expression')
        if not expression:
            raise ValidationError('Custom expression not configured')
        
        try:
            # Create safe evaluation context
            context = {
                'value': value,
                're': re,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
            }
            
            result = eval(expression, {"__builtins__": {}}, context)
            
            if not result:
                raise ValidationError(rule.error_message)
        
        except Exception as e:
            raise ValidationError(f'Custom validation failed: {str(e)}')
    
    def _validate_file_type(self, rule: ValidationRule, value: Any):
        """Validate file type."""
        allowed_types = rule.rule_config.get('allowed_types', [])
        
        if not value:
            return
        
        validator = FileExtensionValidator(allowed_types)
        validator(value)
    
    def _validate_file_size(self, rule: ValidationRule, value: Any):
        """Validate file size."""
        min_size = rule.rule_config.get('min_size')
        max_size = rule.rule_config.get('max_size')
        
        if not value:
            return
        
        validator = FileSizeValidator(min_size=min_size, max_size=max_size)
        validator(value)
    
    def _validate_uniqueness(self, rule: ValidationRule, value: Any):
        """Validate field uniqueness."""
        model_class = self._get_model_class(rule.target_model)
        field_name = rule.target_field
        
        if not model_class or not field_name:
            return
        
        # Check if value exists
        exists = model_class.objects.filter(**{field_name: value}).exists()
        
        if exists:
            raise ValidationError(rule.error_message)
    
    def _validate_relationship(self, rule: ValidationRule, value: Any):
        """Validate relationship constraints."""
        related_model = rule.rule_config.get('related_model')
        related_field = rule.rule_config.get('related_field')
        
        if not related_model or not value:
            return
        
        model_class = self._get_model_class(related_model)
        
        if not model_class:
            return
        
        # Check if related object exists
        if not model_class.objects.filter(id=value).exists():
            raise ValidationError(rule.error_message)
    
    def _validate_business_rule(self, rule: ValidationRule, value: Any):
        """Validate custom business rule."""
        rule_name = rule.rule_config.get('rule_name')
        
        if not rule_name:
            raise ValidationError('Business rule name not configured')
        
        # Call appropriate business rule validator
        if rule_name == 'itar_compliance':
            ITARComplianceValidator()(value)
        
        elif rule_name == 'org_quota':
            quota_type = rule.rule_config.get('quota_type', 'storage')
            OrganizationQuotaValidator(quota_type)(value)
        
        elif rule_name == 'unique_version':
            UniqueVersionValidator()(value)
        
        else:
            raise ValidationError(f'Unknown business rule: {rule_name}')
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _get_model_class(self, model_name: str):
        """Get model class by name."""
        try:
            from designs import models
            return getattr(models, model_name, None)
        except:
            return None
    
    def _generate_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Generate summary from validation results."""
        total = len(results)
        passed = sum(1 for r in results if r.status == 'PASSED')
        failed = sum(1 for r in results if r.status == 'FAILED')
        skipped = sum(1 for r in results if r.status == 'SKIPPED')
        
        by_severity = {}
        for result in results:
            if result.status == 'FAILED':
                severity = result.rule.severity
                by_severity[severity] = by_severity.get(severity, 0) + 1
        
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'pass_rate': round((passed / total * 100), 2) if total > 0 else 0,
            'by_severity': by_severity
        }


# ============================================================================
# VALIDATION DECORATORS
# ============================================================================

def validate_on_save(model_class):
    """
    Decorator to automatically validate model on save.
    
    Usage:
        @validate_on_save
        class MyModel(models.Model):
            ...
    """
    original_save = model_class.save
    
    def wrapped_save(self, *args, **kwargs):
        # Determine operation
        operation = 'update' if self.pk else 'create'
        
        # Run validation
        service = ValidationService()
        is_valid, results = service.validate_model_instance(
            instance=self,
            operation=operation
        )
        
        # Block save if validation failed
        if not is_valid:
            failed = [r for r in results if r.status == 'FAILED']
            errors = [r.error_message for r in failed]
            raise ValidationError('; '.join(errors))
        
        # Proceed with save
        return original_save(self, *args, **kwargs)
    
    model_class.save = wrapped_save
    return model_class


def validate_field(*validators):
    """
    Decorator to validate field value before setting.
    
    Usage:
        @validate_field(PartNumberValidator(), MinLengthValidator(3))
        def set_part_number(self, value):
            self.part_number = value
    """
    def decorator(func):
        def wrapper(self, value):
            for validator in validators:
                validator(value)
            return func(self, value)
        return wrapper
    return decorator
