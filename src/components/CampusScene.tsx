import { Canvas } from '@react-three/fiber';
import { OrbitControls, ContactShadows, Gltf } from '@react-three/drei';
import { Suspense, useMemo } from 'react';
import { useCampus } from '../lib/data';
import { useCampusStore } from '../lib/store';

const CAMPUS_GLB = '/models/campus.glb';

export function CampusScene() {
  const quality = useCampusStore((s) => s.quality);
  const { campus } = useCampus();
  const heightM = useMemo(() => {
    const b = campus?.buildings[0];
    if (b?.bounds) return Math.max(40, (b.bounds.maxZ - b.bounds.minZ) * 2 + 10);
    if (b) return Math.max(40, b.floors * 3.5 * 2 + 10);
    return 90;
  }, [campus]);

  const glbEnabled = quality !== 'low';

  return (
    <Canvas
      dpr={quality === 'high' ? [1, 2] : [1, 1]}
      camera={{ position: [0, heightM, 0] as [number, number, number], fov: 55 }}
      gl={{ antialias: glbEnabled, alpha: true }}
      shadows={glbEnabled}
    >
      <ambientLight intensity={0.7} />
      <directionalLight
        position={[60, 90, 40]}
        intensity={1.6}
        castShadow={glbEnabled}
        shadow-mapSize={[1024, 1024]}
        color="#fff4e0"
      />
      <directionalLight position={[-60, 40, -50]} intensity={0.35} />
      <Suspense fallback={null}>
        {glbEnabled ? <Gltf src={CAMPUS_GLB} /> : null}
      </Suspense>
      <ContactShadows position={[0, 0, 0]} opacity={0.35} scale={400} blur={2.5} far={40} />
      <OrbitControls enablePan={false} enableDamping makeDefault />
    </Canvas>
  );
}
