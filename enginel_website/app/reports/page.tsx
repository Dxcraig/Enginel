'use client';

import React, { useState, useEffect } from 'react';
import ApiClient from '@/lib/api/client';
import { DesignSeries, DesignAsset, AssemblyNode } from '@/types';

type ReportType = 'design-list' | 'design-detail' | 'bom-hierarchy' | 'validation-summary' | 'audit-trail' | 'custom';
type ExportFormat = 'csv' | 'excel' | 'pdf' | 'json';

interface ReportTemplate {
    id: string;
    name: string;
    description: string;
    type: ReportType;
    icon: React.ReactNode;
    formats: ExportFormat[];
}

export default function ReportsPage() {
    const [selectedTemplate, setSelectedTemplate] = useState<ReportType | null>(null);
    const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('csv');
    const [loading, setLoading] = useState(false);

    // Filters for different report types
    const [seriesFilter, setSeriesFilter] = useState('');
    const [dateFrom, setDateFrom] = useState('');
    const [dateTo, setDateTo] = useState('');
    const [includeMetadata, setIncludeMetadata] = useState(true);
    const [selectedSeries, setSelectedSeries] = useState<string>('');

    // Data
    const [seriesList, setSeriesList] = useState<DesignSeries[]>([]);
    const [previewData, setPreviewData] = useState<any>(null);

    useEffect(() => {
        fetchSeries();
    }, []);

    const fetchSeries = async () => {
        try {
            const response = await ApiClient.get<{ results: DesignSeries[] }>('/series/');
            setSeriesList(response.results || []);
        } catch (error) {
            console.error('Failed to fetch series:', error);
        }
    };

    const templates: ReportTemplate[] = [
        {
            id: 'design-list',
            name: 'Design Assets List',
            description: 'Export list of all design assets with metadata',
            type: 'design-list',
            formats: ['csv', 'excel', 'pdf'],
            icon: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
            ),
        },
        {
            id: 'design-detail',
            name: 'Design Detail Report',
            description: 'Comprehensive report for a specific design series',
            type: 'design-detail',
            formats: ['pdf', 'excel'],
            icon: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
            ),
        },
        {
            id: 'bom-hierarchy',
            name: 'BOM Hierarchy',
            description: 'Export Bill of Materials with nested structure',
            type: 'bom-hierarchy',
            formats: ['csv', 'excel', 'json'],
            icon: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                </svg>
            ),
        },
        {
            id: 'validation-summary',
            name: 'Validation Summary',
            description: 'Summary of validation rules and results',
            type: 'validation-summary',
            formats: ['csv', 'pdf'],
            icon: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
            ),
        },
        {
            id: 'audit-trail',
            name: 'Audit Trail Report',
            description: 'Compliance report with audit logs',
            type: 'audit-trail',
            formats: ['csv', 'pdf', 'json'],
            icon: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
            ),
        },
        {
            id: 'custom',
            name: 'Custom Report',
            description: 'Build your own custom report',
            type: 'custom',
            formats: ['csv', 'excel', 'json'],
            icon: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                </svg>
            ),
        },
    ];

    const generateReport = async () => {
        if (!selectedTemplate) return;

        setLoading(true);
        try {
            switch (selectedTemplate) {
                case 'design-list':
                    await exportDesignList();
                    break;
                case 'design-detail':
                    await exportDesignDetail();
                    break;
                case 'bom-hierarchy':
                    await exportBOMHierarchy();
                    break;
                case 'validation-summary':
                    await exportValidationSummary();
                    break;
                case 'audit-trail':
                    await exportAuditTrail();
                    break;
                case 'custom':
                    await exportCustomReport();
                    break;
            }
        } catch (error) {
            console.error('Failed to generate report:', error);
            alert('Failed to generate report. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const exportDesignList = async () => {
        const params = new URLSearchParams();
        if (dateFrom) params.append('created_at_after', dateFrom);
        if (dateTo) params.append('created_at_before', dateTo);

        const response = await ApiClient.get<{ results: DesignAsset[] }>(`/designs/?${params.toString()}`);
        const designs = response.results;

        if (selectedFormat === 'csv') {
            const csv = convertDesignsToCSV(designs);
            downloadFile(csv, 'designs-report.csv', 'text/csv');
        } else if (selectedFormat === 'excel') {
            const csv = convertDesignsToCSV(designs);
            downloadFile(csv, 'designs-report.csv', 'text/csv');
            alert('Excel format coming soon! Downloaded as CSV for now.');
        } else if (selectedFormat === 'pdf') {
            generateDesignsPDF(designs);
        }
    };

    const exportDesignDetail = async () => {
        if (!selectedSeries) {
            alert('Please select a design series');
            return;
        }

        const [seriesRes, designsRes] = await Promise.all([
            ApiClient.get<DesignSeries>(`/series/${selectedSeries}/`),
            ApiClient.get<{ results: DesignAsset[] }>(`/designs/?series=${selectedSeries}`),
        ]);

        const series = seriesRes;
        const designs = designsRes.results;

        if (selectedFormat === 'pdf') {
            generateDetailPDF(series, designs);
        } else {
            const csv = convertDesignsToCSV(designs);
            downloadFile(csv, `${series.part_number}-detail.csv`, 'text/csv');
        }
    };

    const exportBOMHierarchy = async () => {
        if (!selectedSeries) {
            alert('Please select a design series with BOM data');
            return;
        }

        const designsRes = await ApiClient.get<{ results: DesignAsset[] }>(`/designs/?series=${selectedSeries}`);
        const designs = designsRes.results;

        if (designs.length === 0 || !designs[0].id) {
            alert('No designs found for this series');
            return;
        }

        const bomRes = await ApiClient.get<AssemblyNode[]>(`/designs/${designs[0].id}/bom/`);
        const bom = bomRes;

        if (selectedFormat === 'csv') {
            const csv = convertBOMToCSV(bom);
            downloadFile(csv, 'bom-hierarchy.csv', 'text/csv');
        } else if (selectedFormat === 'json') {
            const json = JSON.stringify(bom, null, 2);
            downloadFile(json, 'bom-hierarchy.json', 'application/json');
        } else if (selectedFormat === 'excel') {
            const csv = convertBOMToCSV(bom);
            downloadFile(csv, 'bom-hierarchy.csv', 'text/csv');
            alert('Excel format coming soon! Downloaded as CSV for now.');
        }
    };

    const exportValidationSummary = async () => {
        const [rulesRes, resultsRes] = await Promise.all([
            ApiClient.get<{ results: any[] }>('/validation/rules/'),
            ApiClient.get<{ results: any[] }>('/validation/results/'),
        ]);

        const rules = rulesRes.results;
        const results = resultsRes.results;

        if (selectedFormat === 'csv') {
            const csv = convertValidationToCSV(rules, results);
            downloadFile(csv, 'validation-summary.csv', 'text/csv');
        } else if (selectedFormat === 'pdf') {
            generateValidationPDF(rules, results);
        }
    };

    const exportAuditTrail = async () => {
        const params = new URLSearchParams({ page_size: '10000' });
        if (dateFrom) params.append('timestamp_after', dateFrom);
        if (dateTo) params.append('timestamp_before', dateTo);

        const response = await ApiClient.get<{ results: any[] }>(`/audit-logs/?${params.toString()}`);
        const logs = response.results;

        if (selectedFormat === 'csv') {
            const csv = convertAuditToCSV(logs);
            downloadFile(csv, 'audit-trail.csv', 'text/csv');
        } else if (selectedFormat === 'json') {
            const json = JSON.stringify(logs, null, 2);
            downloadFile(json, 'audit-trail.json', 'application/json');
        } else if (selectedFormat === 'pdf') {
            generateAuditPDF(logs);
        }
    };

    const exportCustomReport = async () => {
        alert('Custom report builder coming soon!');
    };

    // CSV Converters
    const convertDesignsToCSV = (designs: DesignAsset[]): string => {
        const headers = ['File Name', 'Series', 'Version', 'File Size', 'File Type', 'Status', 'Uploaded By', 'Upload Date'];
        const rows = designs.map(d => [
            d.filename || d.file_name || '',
            typeof d.series === 'string' ? d.series : d.series?.part_number || '',
            d.version_label || d.version_number?.toString() || '',
            d.file_size ? `${(d.file_size / 1024 / 1024).toFixed(2)} MB` : '',
            d.file_type || '',
            d.status || '',
            d.uploaded_by || '',
            d.created_at ? new Date(d.created_at).toLocaleDateString() : '',
        ]);

        return [headers.join(','), ...rows.map(row => row.map(cell => `"${cell}"`).join(','))].join('\n');
    };

    const convertBOMToCSV = (nodes: AssemblyNode[]): string => {
        const headers = ['Level', 'Part Name', 'Part Number', 'Type', 'Quantity', 'Reference'];
        const rows: string[][] = [];

        const flatten = (node: AssemblyNode, level: number = 0) => {
            rows.push([
                level.toString(),
                node.component_name || '',
                node.part_number || '',
                node.node_type || '',
                node.quantity?.toString() || '1',
                node.reference_designator || '',
            ]);

            if (node.children) {
                node.children.forEach(child => flatten(child, level + 1));
            }
        };

        nodes.forEach(node => flatten(node));

        return [headers.join(','), ...rows.map(row => row.map(cell => `"${cell}"`).join(','))].join('\n');
    };

    const convertValidationToCSV = (rules: any[], results: any[]): string => {
        const headers = ['Rule Name', 'Type', 'Severity', 'Active', 'Total Checks', 'Failures', 'Success Rate'];
        const rows = rules.map(r => [
            r.name,
            r.rule_type,
            r.severity,
            r.is_active ? 'Yes' : 'No',
            r.total_checks?.toString() || '0',
            r.total_failures?.toString() || '0',
            r.total_checks ? `${(((r.total_checks - (r.total_failures || 0)) / r.total_checks) * 100).toFixed(1)}%` : 'N/A',
        ]);

        return [headers.join(','), ...rows.map(row => row.map(cell => `"${cell}"`).join(','))].join('\n');
    };

    const convertAuditToCSV = (logs: any[]): string => {
        const headers = ['Timestamp', 'User', 'Action', 'Resource Type', 'Resource ID', 'IP Address'];
        const rows = logs.map(log => [
            new Date(log.timestamp).toISOString(),
            log.actor_username,
            log.action_display || log.action,
            log.resource_type,
            log.resource_id,
            log.ip_address || 'N/A',
        ]);

        return [headers.join(','), ...rows.map(row => row.map(cell => `"${cell}"`).join(','))].join('\n');
    };

    // PDF Generators (simplified HTML-based)
    const generateDesignsPDF = (designs: DesignAsset[]) => {
        const html = `
      <html>
        <head>
          <title>Designs Report</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #1e40af; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #1e40af; color: white; }
            tr:nth-child(even) { background-color: #f3f4f6; }
          </style>
        </head>
        <body>
          <h1>Design Assets Report</h1>
          <p>Generated on ${new Date().toLocaleDateString()}</p>
          <table>
            <thead>
              <tr>
                <th>File Name</th>
                <th>Series</th>
                <th>Version</th>
                <th>Status</th>
                <th>Upload Date</th>
              </tr>
            </thead>
            <tbody>
              ${designs.map(d => `
                <tr>
                  <td>${d.filename || d.file_name}</td>
                  <td>${typeof d.series === 'string' ? d.series : d.series?.part_number}</td>
                  <td>${d.version_label || d.version_number}</td>
                  <td>${d.status}</td>
                  <td>${new Date(d.created_at).toLocaleDateString()}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </body>
      </html>
    `;

        const printWindow = window.open('', '_blank');
        if (printWindow) {
            printWindow.document.write(html);
            printWindow.document.close();
            printWindow.print();
        }
    };

    const generateDetailPDF = (series: DesignSeries, designs: DesignAsset[]) => {
        const html = `
      <html>
        <head>
          <title>Design Detail Report - ${series.part_number}</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #1e40af; }
            .info { margin: 20px 0; }
            .info-item { margin: 10px 0; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #1e40af; color: white; }
          </style>
        </head>
        <body>
          <h1>Design Series: ${series.part_number}</h1>
          <div class="info">
            <div class="info-item"><strong>Name:</strong> ${series.name}</div>
            <div class="info-item"><strong>Description:</strong> ${series.description || 'N/A'}</div>
            <div class="info-item"><strong>Status:</strong> ${series.status}</div>
            <div class="info-item"><strong>Classification:</strong> ${series.classification_level}</div>
            <div class="info-item"><strong>Version Count:</strong> ${designs.length}</div>
          </div>
          <h2>Design Assets</h2>
          <table>
            <thead>
              <tr>
                <th>Version</th>
                <th>File Name</th>
                <th>File Type</th>
                <th>Upload Date</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              ${designs.map(d => `
                <tr>
                  <td>${d.version_label || d.version_number}</td>
                  <td>${d.filename || d.file_name}</td>
                  <td>${d.file_type}</td>
                  <td>${new Date(d.created_at).toLocaleDateString()}</td>
                  <td>${d.status}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </body>
      </html>
    `;

        const printWindow = window.open('', '_blank');
        if (printWindow) {
            printWindow.document.write(html);
            printWindow.document.close();
            printWindow.print();
        }
    };

    const generateValidationPDF = (rules: any[], results: any[]) => {
        const html = `
      <html>
        <head>
          <title>Validation Summary Report</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #1e40af; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #1e40af; color: white; }
          </style>
        </head>
        <body>
          <h1>Validation Summary Report</h1>
          <p>Generated on ${new Date().toLocaleDateString()}</p>
          <table>
            <thead>
              <tr>
                <th>Rule Name</th>
                <th>Type</th>
                <th>Severity</th>
                <th>Total Checks</th>
                <th>Failures</th>
              </tr>
            </thead>
            <tbody>
              ${rules.map(r => `
                <tr>
                  <td>${r.name}</td>
                  <td>${r.rule_type}</td>
                  <td>${r.severity}</td>
                  <td>${r.total_checks || 0}</td>
                  <td>${r.total_failures || 0}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </body>
      </html>
    `;

        const printWindow = window.open('', '_blank');
        if (printWindow) {
            printWindow.document.write(html);
            printWindow.document.close();
            printWindow.print();
        }
    };

    const generateAuditPDF = (logs: any[]) => {
        const html = `
      <html>
        <head>
          <title>Audit Trail Report</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #1e40af; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12px; }
            th, td { border: 1px solid #ddd; padding: 6px; text-align: left; }
            th { background-color: #1e40af; color: white; }
          </style>
        </head>
        <body>
          <h1>Audit Trail Report</h1>
          <p>Generated on ${new Date().toLocaleDateString()}</p>
          <p>Total Events: ${logs.length}</p>
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>User</th>
                <th>Action</th>
                <th>Resource</th>
                <th>IP Address</th>
              </tr>
            </thead>
            <tbody>
              ${logs.slice(0, 100).map(log => `
                <tr>
                  <td>${new Date(log.timestamp).toLocaleString()}</td>
                  <td>${log.actor_username}</td>
                  <td>${log.action_display || log.action}</td>
                  <td>${log.resource_type}</td>
                  <td>${log.ip_address || 'N/A'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
          ${logs.length > 100 ? '<p><em>Showing first 100 entries only</em></p>' : ''}
        </body>
      </html>
    `;

        const printWindow = window.open('', '_blank');
        if (printWindow) {
            printWindow.document.write(html);
            printWindow.document.close();
            printWindow.print();
        }
    };

    const downloadFile = (content: string, filename: string, mimeType: string) => {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900">Reports & Export</h1>
                <p className="mt-2 text-gray-600">Generate and export reports in various formats</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Templates */}
                <div className="lg:col-span-2">
                    <h2 className="text-xl font-semibold text-gray-900 mb-4">Report Templates</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {templates.map((template) => (
                            <button
                                key={template.id}
                                onClick={() => {
                                    setSelectedTemplate(template.type);
                                    setSelectedFormat(template.formats[0]);
                                }}
                                className={`p-6 rounded-lg border-2 transition-all text-left ${selectedTemplate === template.type
                                        ? 'border-blue-600 bg-blue-50'
                                        : 'border-gray-200 hover:border-blue-300 bg-white'
                                    }`}
                            >
                                <div className="flex items-start space-x-4">
                                    <div className={`flex-shrink-0 ${selectedTemplate === template.type ? 'text-blue-600' : 'text-gray-400'}`}>
                                        {template.icon}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <h3 className="text-lg font-semibold text-gray-900 mb-1">
                                            {template.name}
                                        </h3>
                                        <p className="text-sm text-gray-600 mb-3">{template.description}</p>
                                        <div className="flex flex-wrap gap-2">
                                            {template.formats.map((format) => (
                                                <span
                                                    key={format}
                                                    className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded"
                                                >
                                                    {format.toUpperCase()}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Configuration Panel */}
                <div className="lg:col-span-1">
                    <div className="bg-white rounded-lg shadow p-6 sticky top-4">
                        <h2 className="text-xl font-semibold text-gray-900 mb-4">Report Configuration</h2>

                        {selectedTemplate ? (
                            <div className="space-y-4">
                                {/* Format Selection */}
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Export Format
                                    </label>
                                    <select
                                        value={selectedFormat}
                                        onChange={(e) => setSelectedFormat(e.target.value as ExportFormat)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    >
                                        {templates.find(t => t.type === selectedTemplate)?.formats.map((format) => (
                                            <option key={format} value={format}>
                                                {format.toUpperCase()}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                {/* Series Selection (for detail and BOM reports) */}
                                {(selectedTemplate === 'design-detail' || selectedTemplate === 'bom-hierarchy') && (
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Design Series
                                        </label>
                                        <select
                                            value={selectedSeries}
                                            onChange={(e) => setSelectedSeries(e.target.value)}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        >
                                            <option value="">Select series...</option>
                                            {seriesList.map((series) => (
                                                <option key={series.id} value={series.id}>
                                                    {series.part_number} - {series.name}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                )}

                                {/* Date Range */}
                                {(selectedTemplate === 'design-list' || selectedTemplate === 'audit-trail') && (
                                    <>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                                Date From
                                            </label>
                                            <input
                                                type="date"
                                                value={dateFrom}
                                                onChange={(e) => setDateFrom(e.target.value)}
                                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                                Date To
                                            </label>
                                            <input
                                                type="date"
                                                value={dateTo}
                                                onChange={(e) => setDateTo(e.target.value)}
                                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            />
                                        </div>
                                    </>
                                )}

                                {/* Include Metadata */}
                                <div className="flex items-center">
                                    <input
                                        type="checkbox"
                                        id="metadata"
                                        checked={includeMetadata}
                                        onChange={(e) => setIncludeMetadata(e.target.checked)}
                                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                    />
                                    <label htmlFor="metadata" className="ml-2 block text-sm text-gray-700">
                                        Include metadata
                                    </label>
                                </div>

                                {/* Generate Button */}
                                <button
                                    onClick={generateReport}
                                    disabled={loading}
                                    className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {loading ? (
                                        <>
                                            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                                            <span>Generating...</span>
                                        </>
                                    ) : (
                                        <>
                                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                            </svg>
                                            <span>Generate Report</span>
                                        </>
                                    )}
                                </button>
                            </div>
                        ) : (
                            <div className="text-center py-8">
                                <svg className="w-12 h-12 text-gray-400 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                                <p className="text-gray-600">Select a report template to begin</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Recent Reports */}
            <div className="mt-8">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Recent Reports</h2>
                <div className="bg-white rounded-lg shadow">
                    <div className="p-6 text-center text-gray-500">
                        <svg className="w-12 h-12 text-gray-400 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <p>Report history coming soon</p>
                        <p className="text-sm mt-1">Your generated reports will appear here</p>
                    </div>
                </div>
            </div>
        </div>
    );
}
