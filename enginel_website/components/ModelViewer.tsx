'use client';

import { Suspense, useState, useRef } from 'react';
import { Canvas, useThree, useFrame } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Grid, Box, Environment, ContactShadows, useGLTF } from '@react-three/drei';
import * as THREE from 'three';

interface ModelViewerProps {
    modelUrl?: string;
    fileType?: string;
    fileName?: string;
}

function FallbackModel() {
    const meshRef = useRef<THREE.Mesh>(null);

    useFrame((state) => {
        if (meshRef.current) {
            meshRef.current.rotation.y = state.clock.getElapsedTime() * 0.3;
        }
    });

    return (
        <group>
            <Box ref={meshRef} args={[2, 2, 2]}>
                <meshStandardMaterial color="#3b82f6" metalness={0.5} roughness={0.3} />
            </Box>
            <ContactShadows
                position={[0, -1.5, 0]}
                opacity={0.5}
                scale={10}
                blur={2}
                far={4}
            />
        </group>
    );
}

function ModelContent({ modelUrl, fileType }: { modelUrl?: string; fileType?: string }) {
    if (!modelUrl) {
        return <FallbackModel />;
    }

    // For now, show fallback. In production, you'd load different model types here
    // based on fileType (STEP, STL, OBJ, etc.)
    return <FallbackModel />;
}

function LoadingFallback() {
    return (
        <mesh>
            <boxGeometry args={[1, 1, 1]} />
            <meshStandardMaterial color="#6b7280" wireframe />
        </mesh>
    );
}

export default function ModelViewer({ modelUrl, fileType, fileName }: ModelViewerProps) {
    const [wireframe, setWireframe] = useState(false);
    const [showGrid, setShowGrid] = useState(true);
    const [autoRotate, setAutoRotate] = useState(false);

    return (
        <div className="relative w-full h-full bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
            {/* 3D Canvas */}
            <Canvas shadows>
                <PerspectiveCamera makeDefault position={[5, 5, 5]} fov={50} />

                {/* Lighting */}
                <ambientLight intensity={0.5} />
                <directionalLight
                    position={[10, 10, 5]}
                    intensity={1}
                    castShadow
                    shadow-mapSize-width={2048}
                    shadow-mapSize-height={2048}
                />
                <pointLight position={[-10, -10, -10]} intensity={0.5} />

                {/* Environment */}
                <Environment preset="studio" />

                {/* Grid */}
                {showGrid && (
                    <Grid
                        args={[20, 20]}
                        cellSize={1}
                        cellThickness={0.5}
                        cellColor="#6b7280"
                        sectionSize={5}
                        sectionThickness={1}
                        sectionColor="#3b82f6"
                        fadeDistance={30}
                        fadeStrength={1}
                        position={[0, -1.5, 0]}
                    />
                )}

                {/* Model */}
                <Suspense fallback={<LoadingFallback />}>
                    <ModelContent modelUrl={modelUrl} fileType={fileType} />
                </Suspense>

                {/* Controls */}
                <OrbitControls
                    enableDamping
                    dampingFactor={0.05}
                    autoRotate={autoRotate}
                    autoRotateSpeed={1}
                    minDistance={2}
                    maxDistance={20}
                />
            </Canvas>

            {/* Control Panel */}
            <div className="absolute top-4 left-4 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-4 space-y-3">
                <div className="text-sm font-semibold text-gray-900 mb-2">
                    View Controls
                </div>

                <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                        type="checkbox"
                        checked={wireframe}
                        onChange={(e) => setWireframe(e.target.checked)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">Wireframe</span>
                </label>

                <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                        type="checkbox"
                        checked={showGrid}
                        onChange={(e) => setShowGrid(e.target.checked)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">Show Grid</span>
                </label>

                <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                        type="checkbox"
                        checked={autoRotate}
                        onChange={(e) => setAutoRotate(e.target.checked)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">Auto Rotate</span>
                </label>

                <div className="pt-2 border-t border-gray-200">
                    <div className="text-xs text-gray-500">
                        <div className="font-medium mb-1">Controls:</div>
                        <div>• Left click + drag: Rotate</div>
                        <div>• Right click + drag: Pan</div>
                        <div>• Scroll: Zoom</div>
                    </div>
                </div>
            </div>

            {/* File Info */}
            {fileName && (
                <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg px-4 py-2">
                    <div className="text-xs text-gray-500">File</div>
                    <div className="text-sm font-medium text-gray-900">{fileName}</div>
                    {fileType && (
                        <div className="text-xs text-gray-600 mt-1">Type: {fileType}</div>
                    )}
                </div>
            )}

            {/* View Angles Quick Actions */}
            <div className="absolute bottom-4 right-4 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-2">
                <div className="text-xs text-gray-500 mb-2 px-2">Quick Views</div>
                <div className="grid grid-cols-2 gap-2">
                    <button
                        className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded transition-colors"
                        onClick={() => {/* TODO: Set camera to front view */ }}
                    >
                        Front
                    </button>
                    <button
                        className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded transition-colors"
                        onClick={() => {/* TODO: Set camera to top view */ }}
                    >
                        Top
                    </button>
                    <button
                        className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded transition-colors"
                        onClick={() => {/* TODO: Set camera to side view */ }}
                    >
                        Side
                    </button>
                    <button
                        className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded transition-colors"
                        onClick={() => {/* TODO: Set camera to isometric view */ }}
                    >
                        ISO
                    </button>
                </div>
            </div>
        </div>
    );
}
