'use client';

import { useState } from 'react';
import { AssemblyNode } from '@/types';

interface TreeNodeProps {
    node: AssemblyNode;
    level: number;
}

function TreeNode({ node, level }: TreeNodeProps) {
    const [isExpanded, setIsExpanded] = useState(level < 2);

    const hasChildren = node.children && node.children.length > 0;
    const indent = level * 24;

    return (
        <div>
            <div
                className="flex items-center py-2 px-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100"
                style={{ paddingLeft: `${indent + 12}px` }}
            >
                {/* Expand/Collapse Button */}
                <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="mr-2 w-6 h-6 flex items-center justify-center text-gray-500 hover:text-gray-700"
                    disabled={!hasChildren}
                >
                    {hasChildren ? (
                        isExpanded ? (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                        ) : (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                        )
                    ) : (
                        <span className="text-gray-300">•</span>
                    )}
                </button>

                {/* Node Icon */}
                <div className="mr-3">
                    {node.node_type === 'assembly' ? (
                        <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                        </svg>
                    ) : (
                        <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                    )}
                </div>

                {/* Node Info */}
                <div className="flex-1 flex items-center justify-between">
                    <div>
                        <div className="font-medium text-gray-900">{node.component_name}</div>
                        {node.part_number && (
                            <div className="text-sm text-gray-500">{node.part_number}</div>
                        )}
                    </div>
                    <div className="flex items-center space-x-4 text-sm text-gray-500">
                        {node.quantity && (
                            <div className="flex items-center">
                                <span className="font-medium">Qty:</span>
                                <span className="ml-1">{node.quantity}</span>
                            </div>
                        )}
                        {node.reference_designator && (
                            <div className="text-gray-400">{node.reference_designator}</div>
                        )}
                        <span className={`px-2 py-1 text-xs rounded-full ${node.node_type === 'assembly' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'
                            }`}>
                            {node.node_type}
                        </span>
                    </div>
                </div>
            </div>

            {/* Children */}
            {hasChildren && isExpanded && (
                <div>
                    {node.children!.map((child) => (
                        <TreeNode key={child.id} node={child} level={level + 1} />
                    ))}
                </div>
            )}
        </div>
    );
}

interface BOMTreeProps {
    nodes: AssemblyNode[];
}

export default function BOMTree({ nodes }: BOMTreeProps) {
    if (!nodes || nodes.length === 0) {
        return (
            <div className="text-center py-12 text-gray-500">
                No assembly structure defined. Upload a design file with BOM information.
            </div>
        );
    }

    return (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            {nodes.map((node) => (
                <TreeNode key={node.id} node={node} level={0} />
            ))}
        </div>
    );
}
