import { Canvas } from '@react-three/fiber';
import { OrbitControls, ContactShadows, Gltf } from '@react-three/drei';
import { Suspense } from 'react';
import { useCampusStore } from '../lib/store';

const CAMPUS_GLB = '/models/campus.glb';

export function CampusScene() {
  const quality = useCampusStore((s) => s.quality);
  const glbEnabled = quality !== 'low';

  return (
    <Canvas
      dpr={quality === 'high' ? [1, 2] : [1, 1]}
      camera={{ position: [520, 620, 780], fov: 50, near: 1, far: 20000 }}
      gl={{ antialias: glbEnabled, alpha: true }}
      shadows={glbEnabled}
    >
      <ambientLight intensity={0.7} />
      <directionalLight
        position={[300, 500, 200]}
        intensity={1.6}
        castShadow={glbEnabled}
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-1200}
        shadow-camera-right={1200}
        shadow-camera-top={1200}
        shadow-camera-bottom={-1200}
        shadow-camera-far={4000}
        color="#fff4e0"
      />
      <directionalLight position={[-300, 200, -250]} intensity={0.35} />
      <Suspense fallback={null}>
        {glbEnabled ? <Gltf src={CAMPUS_GLB} /> : null}
      </Suspense>
      <ContactShadows position={[0, 0.1, 0]} opacity={0.35} scale={4200} blur={2.5} far={60} />
      <OrbitControls enablePan enableDamping makeDefault target={[0, 0, 0]} maxDistance={8000} />
    </Canvas>
  );
}
