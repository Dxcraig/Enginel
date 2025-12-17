'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

interface AssemblyNode {
    id: string;
    design_asset: string;
    name: string;
    part_number: string;
    quantity: number;
    reference_designator: string;
    node_type: 'ASSEMBLY' | 'SUBASSEMBLY' | 'PART' | 'HARDWARE';
    mass: number | null;
    volume: number | null;
    component_metadata: any;
    depth: number;
    numchild: number;
    path: string;
}

interface BOMSummary {
    totalParts: number;
    uniqueParts: number;
    totalMass: number;
    assemblies: number;
    parts: number;
    hardware: number;
}

export default function BOMPage() {
    const router = useRouter();
    const [nodes, setNodes] = useState<AssemblyNode[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [nodeTypeFilter, setNodeTypeFilter] = useState('all');
    const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
    const [summary, setSummary] = useState<BOMSummary>({
        totalParts: 0,
        uniqueParts: 0,
        totalMass: 0,
        assemblies: 0,
        parts: 0,
        hardware: 0,
    });

    useEffect(() => {
        fetchBOMData();
    }, [nodeTypeFilter]);

    const fetchBOMData = async () => {
        try {
            setLoading(true);
            const token = localStorage.getItem('enginel_auth_token');

            let url = 'http://localhost:8000/api/bom-nodes/';
            const params = new URLSearchParams();

            if (nodeTypeFilter !== 'all') {
                params.append('node_type', nodeTypeFilter);
            }

            if (params.toString()) {
                url += '?' + params.toString();
            }

            const response = await fetch(url, {
                headers: {
                    'Authorization': `Token ${token}`,
                },
            });

            if (response.ok) {
                const data = await response.json();
                const bomNodes = data.results || data;
                setNodes(bomNodes);
                calculateSummary(bomNodes);
            }
        } catch (err) {
            console.error('Error fetching BOM data:', err);
        } finally {
            setLoading(false);
        }
    };

    const calculateSummary = (bomNodes: AssemblyNode[]) => {
        const uniquePartNumbers = new Set(bomNodes.map(n => n.part_number).filter(Boolean));
        const totalQuantity = bomNodes.reduce((sum, node) => sum + node.quantity, 0);
        const totalMass = bomNodes.reduce((sum, node) => sum + ((node.mass || 0) * node.quantity), 0);

        const assemblies = bomNodes.filter(n => n.node_type === 'ASSEMBLY' || n.node_type === 'SUBASSEMBLY').length;
        const parts = bomNodes.filter(n => n.node_type === 'PART').length;
        const hardware = bomNodes.filter(n => n.node_type === 'HARDWARE').length;

        setSummary({
            totalParts: totalQuantity,
            uniqueParts: uniquePartNumbers.size,
            totalMass: totalMass,
            assemblies,
            parts,
            hardware,
        });
    };

    const toggleNodeExpansion = (nodeId: string) => {
        const newExpanded = new Set(expandedNodes);
        if (newExpanded.has(nodeId)) {
            newExpanded.delete(nodeId);
        } else {
            newExpanded.add(nodeId);
        }
        setExpandedNodes(newExpanded);
    };

    const getNodeTypeColor = (type: string) => {
        switch (type) {
            case 'ASSEMBLY': return 'bg-blue-100 text-blue-800 border-blue-200';
            case 'SUBASSEMBLY': return 'bg-purple-100 text-purple-800 border-purple-200';
            case 'PART': return 'bg-green-100 text-green-800 border-green-200';
            case 'HARDWARE': return 'bg-orange-100 text-orange-800 border-orange-200';
            default: return 'bg-gray-100 text-gray-800 border-gray-200';
        }
    };

    const getNodeIcon = (type: string) => {
        switch (type) {
            case 'ASSEMBLY':
                return (
                    <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                );
            case 'SUBASSEMBLY':
                return (
                    <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                    </svg>
                );
            case 'PART':
                return (
                    <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                    </svg>
                );
            case 'HARDWARE':
                return (
                    <svg className="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                );
            default:
                return null;
        }
    };

    const buildHierarchy = (nodes: AssemblyNode[]) => {
        // Group nodes by parent path
        const roots = nodes.filter(n => n.depth === 0);
        const nodeMap = new Map(nodes.map(n => [n.id, n]));

        return roots;
    };

    const getChildrenNodes = (parentPath: string, depth: number) => {
        return nodes.filter(n =>
            n.path.startsWith(parentPath) &&
            n.depth === depth + 1 &&
            n.path.split('/').length === parentPath.split('/').length + 1
        );
    };

    const renderNode = (node: AssemblyNode) => {
        const hasChildren = node.numchild > 0;
        const isExpanded = expandedNodes.has(node.id);
        const children = hasChildren ? getChildrenNodes(node.path, node.depth) : [];
        const indentLevel = node.depth * 24;

        return (
            <div key={node.id}>
                <div
                    className="flex items-center gap-3 p-3 hover:bg-gray-50 border-b border-gray-100 transition-colors"
                    style={{ paddingLeft: `${16 + indentLevel}px` }}
                >
                    {/* Expand/Collapse Button */}
                    {hasChildren && (
                        <button
                            onClick={() => toggleNodeExpansion(node.id)}
                            className="flex-shrink-0 w-6 h-6 flex items-center justify-center hover:bg-gray-200 rounded transition-colors"
                        >
                            {isExpanded ? (
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                            ) : (
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                </svg>
                            )}
                        </button>
                    )}
                    {!hasChildren && <div className="w-6" />}

                    {/* Node Icon */}
                    <div className="flex-shrink-0">
                        {getNodeIcon(node.node_type)}
                    </div>

                    {/* Node Name & Part Number */}
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900">{node.name}</span>
                            {node.part_number && (
                                <span className="text-sm text-gray-500">({node.part_number})</span>
                            )}
                        </div>
                        {node.reference_designator && (
                            <span className="text-xs text-gray-500">{node.reference_designator}</span>
                        )}
                    </div>

                    {/* Node Type Badge */}
                    <span className={`px-2 py-1 text-xs font-medium rounded border ${getNodeTypeColor(node.node_type)}`}>
                        {node.node_type}
                    </span>

                    {/* Quantity */}
                    <div className="text-sm font-medium text-gray-700 w-20 text-center">
                        x{node.quantity}
                    </div>

                    {/* Mass */}
                    {node.mass && (
                        <div className="text-sm text-gray-600 w-24 text-right">
                            {(node.mass * node.quantity).toFixed(3)} kg
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex-shrink-0 flex items-center gap-2">
                        <button
                            onClick={() => router.push(`/designs/${node.design_asset}`)}
                            className="text-blue-600 hover:text-blue-800"
                            title="View Design"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                        </button>
                    </div>
                </div>

                {/* Render Children */}
                {isExpanded && hasChildren && (
                    <div>
                        {children.map(child => renderNode(child))}
                    </div>
                )}
            </div>
        );
    };

    const filteredNodes = nodes.filter(node => {
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            return (
                node.name.toLowerCase().includes(query) ||
                node.part_number.toLowerCase().includes(query) ||
                node.reference_designator.toLowerCase().includes(query)
            );
        }
        return true;
    });

    const rootNodes = buildHierarchy(filteredNodes);

    return (
        <div className="min-h-screen bg-gray-50 py-8 px-4">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Bill of Materials</h1>
                    <p className="text-gray-600">Manage and visualize assembly hierarchies and component lists</p>
                </div>

                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-600 mb-1">Total Parts</p>
                                <p className="text-2xl font-bold text-gray-900">{summary.totalParts}</p>
                            </div>
                            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                                </svg>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-600 mb-1">Unique Parts</p>
                                <p className="text-2xl font-bold text-gray-900">{summary.uniqueParts}</p>
                            </div>
                            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                </svg>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-600 mb-1">Total Mass</p>
                                <p className="text-2xl font-bold text-gray-900">{summary.totalMass.toFixed(2)} kg</p>
                            </div>
                            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
                                </svg>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-600 mb-1">Assemblies</p>
                                <p className="text-2xl font-bold text-gray-900">{summary.assemblies}</p>
                            </div>
                            <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                                <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                                </svg>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Filters & Search */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
                    <div className="flex flex-col md:flex-row gap-4">
                        <div className="flex-1">
                            <label className="block text-sm font-medium text-gray-700 mb-2">Search</label>
                            <div className="relative">
                                <input
                                    type="text"
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    placeholder="Search by name, part number, or reference..."
                                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                />
                                <svg className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                </svg>
                            </div>
                        </div>

                        <div className="w-full md:w-64">
                            <label className="block text-sm font-medium text-gray-700 mb-2">Node Type</label>
                            <select
                                value={nodeTypeFilter}
                                onChange={(e) => setNodeTypeFilter(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            >
                                <option value="all">All Types</option>
                                <option value="ASSEMBLY">Assembly</option>
                                <option value="SUBASSEMBLY">Sub-Assembly</option>
                                <option value="PART">Part</option>
                                <option value="HARDWARE">Hardware</option>
                            </select>
                        </div>

                        <div className="flex items-end gap-2">
                            <button
                                onClick={() => {
                                    setExpandedNodes(new Set(nodes.map(n => n.id)));
                                }}
                                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                            >
                                Expand All
                            </button>
                            <button
                                onClick={() => setExpandedNodes(new Set())}
                                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                            >
                                Collapse All
                            </button>
                        </div>
                    </div>
                </div>

                {/* BOM Tree */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                    <div className="bg-gray-50 border-b border-gray-200 p-4">
                        <div className="flex items-center gap-3 font-medium text-sm text-gray-700" style={{ paddingLeft: '46px' }}>
                            <div className="w-5" />
                            <div className="flex-1">Component</div>
                            <div className="w-32">Type</div>
                            <div className="w-20 text-center">Quantity</div>
                            <div className="w-24 text-right">Mass</div>
                            <div className="w-12">Actions</div>
                        </div>
                    </div>

                    <div className="divide-y divide-gray-100">
                        {loading ? (
                            <div className="p-12 text-center">
                                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                                <p className="mt-4 text-gray-600">Loading BOM data...</p>
                            </div>
                        ) : filteredNodes.length === 0 ? (
                            <div className="p-12 text-center">
                                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                                </svg>
                                <h3 className="mt-4 text-lg font-medium text-gray-900">No BOM Data Found</h3>
                                <p className="mt-2 text-gray-600">Upload designs with assembly structures to populate the BOM.</p>
                            </div>
                        ) : (
                            rootNodes.map(node => renderNode(node))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
