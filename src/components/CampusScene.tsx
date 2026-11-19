import { Canvas } from '@react-three/fiber';
import { OrbitControls, ContactShadows, Gltf } from '@react-three/drei';
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { loadScatter } from '../lib/data';
import { getSunInfo, nightFactor } from '../lib/sun';
import { useCampusStore } from '../lib/store';
import type { ScatterEntry } from '../lib/types';
import { RouteRenderer } from './RouteRenderer';
import { CameraFocus } from './CameraFocus';
import { SkyDome } from './SkyDome';
import { StreetLamps } from './StreetLamps';

const CAMPUS_GLB = '/models/campus.glb';

function applyNight(scene: THREE.Group | null, glow: number) {
  if (!scene) return;
  scene.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (!mesh.isMesh) return;
    const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const m of mats) {
      const mat = m as THREE.MeshStandardMaterial;
      if (!mat || !mat.emissive) continue;
      // 7-9: only MAT_wall carries the repeating window emissive atlas. Other
      // materials stay dark instead of making the whole building glow.
      const isWall = mat.name === 'MAT_wall';
      mat.emissive.set(isWall ? '#ffffff' : '#000000');
      mat.emissiveIntensity = isWall ? glow * 1.6 : 0;
    }
  });
}

function Trees({ scatter }: { scatter: ScatterEntry[] }) {
  const ref = useRef<THREE.InstancedMesh>(null);
  const treeMat = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: new THREE.Color('#2e5d34'),
        roughness: 1.0,
        flatShading: true,
      }),
    [],
  );
  const geometry = useMemo(() => new THREE.ConeGeometry(0.9, 2.2, 6), []);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const instances = useMemo(() => {
    const n = Math.min(scatter.length, 1024);
    const matrices = new Array<THREE.Matrix4>(n);
    for (let i = 0; i < n; i++) {
      const t = scatter[i % Math.max(scatter.length, 1)];
      dummy.position.set(t.position[0], 0, t.position[2]);
      dummy.scale.setScalar(t.scale ?? 1);
      dummy.rotation.set(t.rotation?.[0] ?? 0, t.rotation?.[1] ?? 0, 0);
      dummy.updateMatrix();
      matrices[i] = dummy.matrix.clone();
    }
    return { n, matrices };
  }, [scatter, dummy]);

  useEffect(() => {
    const mesh = ref.current;
    if (!mesh) return;
    for (let i = 0; i < instances.n; i++) {
      mesh.setMatrixAt(i, instances.matrices[i]);
    }
    mesh.count = instances.n;
    mesh.instanceMatrix.needsUpdate = true;
  }, [instances]);

  if (instances.n < 1) return null;
  return <instancedMesh ref={ref} args={[geometry, treeMat, instances.n]} frustumCulled={false} />;
}

export function CampusScene() {
  const quality = useCampusStore((s) => s.quality);
  const glbEnabled = quality !== 'low';
  const night = useCampusStore((s) => s.night);
  const sunUtcMs = useCampusStore((s) => s.sunUtcMs);
  const route = useCampusStore((s) => s.route);
  const [scatter, setScatter] = useState<ScatterEntry[]>([]);
  const lamps = useMemo(() => scatter.filter((s) => s.type === 'lamp'), [scatter]);
  const trees = useMemo(() => scatter.filter((s) => s.type === 'tree'), [scatter]);
  const gltfRef = useRef<THREE.Group>(null);

  // Time-of-day lighting (7-7): the solar model drives the key light's
  // direction, colour and intensity. `dim` = manual night toggle OR the sun
  // below the horizon at the selected time — windows glow in either case.
  const sun = useMemo(() => getSunInfo(sunUtcMs), [sunUtcMs]);
  const nightGlow = Math.max(night ? 1 : 0, nightFactor(sun));
  const dim = nightGlow > 0.5;
  const elevation = Math.max(sun.elevationDeg, 0);
  const day = Math.min(elevation / 30, 1);
  const keyIntensity = dim ? 0.15 : 0.4 + 1.2 * day;
  const keyColor = dim ? '#8fa8dd' : elevation < 12 ? '#ffc98a' : '#fff4e0';
  const ambientIntensity = dim ? 0.25 : 0.4 + 0.3 * day;
  const keyPosition = useMemo<[number, number, number]>(() => {
    const az = (sun.azimuthDeg * Math.PI) / 180;
    const el = (Math.max(sun.elevationDeg, 6) * Math.PI) / 180;
    // Scene axes: x = east, y = up, z = −north.
    const r = 900;
    return [Math.cos(el) * Math.sin(az) * r, Math.sin(el) * r, -Math.cos(el) * Math.cos(az) * r];
  }, [sun.azimuthDeg, sun.elevationDeg]);

  useEffect(() => {
    let cancelled = false;
    loadScatter()
      .then((s) => {
        if (!cancelled) setScatter(s);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    applyNight(gltfRef.current, nightGlow);
  }, [nightGlow]);

  // Low quality never loads the GLB, so data alone is enough to release the loader.
  useEffect(() => {
    if (!glbEnabled) useCampusStore.getState().setModelReady(true);
  }, [glbEnabled]);

  // Attach the loaded model: hide the ENTR_* entrance markers (they are visual
  // anchors for nav.json, which routing uses by id — the meshes are not needed)
  // and apply the current night state (the [night] effect may have run while
  // Suspense still held the model).
  const attachGltf = useCallback((group: THREE.Group | null) => {
    gltfRef.current = group;
    if (!group) return;
    // 7-10: the GLB has attached — release the loading screen.
    useCampusStore.getState().setModelReady(true);
    group.traverse((obj) => {
      if (obj.name.startsWith('ENTR_')) obj.visible = false;
    });
    const st = useCampusStore.getState();
    applyNight(group, Math.max(st.night ? 1 : 0, nightFactor(getSunInfo(st.sunUtcMs))));
  }, []);

  return (
    <Canvas
      dpr={quality === 'high' ? [1, 2] : [1, 1]}
      camera={{ position: [1150, 1500, 1750], fov: 50, near: 1, far: 20000 }}
      gl={{ antialias: glbEnabled, alpha: true }}
      shadows={glbEnabled}
    >
      <SkyDome />
      <ambientLight intensity={ambientIntensity} />
      <directionalLight position={keyPosition} intensity={keyIntensity} castShadow={glbEnabled} shadow-mapSize={[2048, 2048]} color={keyColor} />
      <directionalLight position={[-300, 200, -250]} intensity={dim ? 0.1 : 0.35} />
      <Suspense fallback={null}>
        {glbEnabled ? <Gltf src={CAMPUS_GLB} ref={attachGltf} /> : null}
      </Suspense>
      <Trees scatter={trees} />
      <StreetLamps lamps={lamps} />
      {/* Route line must render inside the Canvas (drei <Line> needs R3F context) */}
      {route && <RouteRenderer fromId={route.fromId} toId={route.toId} />}
      <CameraFocus />
      <ContactShadows position={[0, 0.1, 0]} opacity={0.35} scale={2500} blur={2.5} far={60} />
      <OrbitControls enablePan enableDamping makeDefault target={[0, 0, 0]} maxDistance={8000} />
    </Canvas>
  );
}
