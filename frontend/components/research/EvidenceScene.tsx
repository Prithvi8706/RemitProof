"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Line, Text } from "@react-three/drei";
import { useRef } from "react";
import type { Group } from "three";
import { scrollVelocity } from "./ResearchRuntime";

const alternatives: [number, number, number][][] = [
  [[-5, -1.2, 0], [-3.4, -0.8, 0], [-1.2, 0.5, 0], [1.1, -0.3, 0], [4.7, -0.7, 0]],
  [[-5, -1.2, 0], [-3.2, -0.4, 0], [-1.3, -0.7, 0], [1.4, 0.4, 0], [4.7, -0.3, 0]],
  [[-5, -1.2, 0], [-3.5, -1, 0], [-1, -0.2, 0], [1.7, -0.8, 0], [4.7, -1.05, 0]],
];

function EvidenceGraph() {
  const group = useRef<Group>(null);
  useFrame((state) => {
    if (!group.current) return;
    const velocity = scrollVelocity.current;
    group.current.rotation.x += ((velocity * 0.014) - group.current.rotation.x) * 0.08;
    group.current.rotation.y += ((velocity * 0.01) - group.current.rotation.y) * 0.08;
    group.current.position.y = Math.sin(state.clock.elapsedTime * 0.22) * 0.025;
  });
  return (
    <group ref={group}>
      {alternatives.map((points, index) => <Line key={index} points={points} color="#6e6e73" lineWidth={0.65} dashed dashSize={0.12} gapSize={0.1} transparent opacity={0.35 - index * 0.06} />)}
      <Line points={[[-5,-1.2,0.1],[-3.5,-0.65,0.1],[-1.7,0.1,0.1],[0.2,0.72,0.1],[2.4,1.15,0.1],[4.7,1.22,0.1]]} color="#f5f5f7" lineWidth={1.5} />
      <mesh position={[4.7,1.22,0.1]}><sphereGeometry args={[0.085,24,24]} /><meshBasicMaterial color="#10b981" /></mesh>
      <Text position={[-4.95,-1.55,0]} fontSize={0.18} color="#86868b" anchorX="left">PROPOSAL</Text>
      <Text position={[4.75,1.48,0]} fontSize={0.18} color="#10b981" anchorX="right">VERIFIED EVIDENCE</Text>
      <Text position={[4.75,-1.42,0]} fontSize={0.15} color="#6e6e73" anchorX="right">ALTERNATIVES ELIMINATED</Text>
    </group>
  );
}

export default function EvidenceScene() {
  return (
    <Canvas aria-hidden="true" orthographic camera={{ position: [0,0,10], zoom: 75 }} dpr={[1,2]} gl={{ alpha: true, antialias: true, powerPreference: "low-power" }}>
      <EvidenceGraph />
    </Canvas>
  );
}
