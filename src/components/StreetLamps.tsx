'use client';

import { useThree } from '@react-three/fiber';
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { getSunInfo, nightFactor } from '../lib/sun';
import { useCampusStore } from '../lib/store';
import type { ScatterEntry } from '../lib/types';

const POLE_HEIGHT = 7;
const HEAD_HEIGHT = POLE_HEIGHT + 0.25;

/** Soft white disc fading to transparent at the rim (runtime-only, no GLB texture). */
function glowTexture(): THREE.CanvasTexture | null {
  if (typeof document === 'undefined') return null;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 64;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.4, 'rgba(255,255,255,0.35)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(canvas);
}

/**
 * Phase 7 item 7-8: street lamps from `scatter.json` (`SCAT_lamp_*`), drawn as
 * three instanced draw calls (post, glowing head, ground pool) plus one Points
 * halo. Everything is procedural at runtime — the GLB stays at 4 materials /
 * 0 textures — and the glow follows the same night factor as the sky.
 */
export function StreetLamps({ lamps }: { lamps: ScatterEntry[] }) {
  const poleRef = useRef<THREE.InstancedMesh>(null);
  const headRef = useRef<THREE.InstancedMesh>(null);
  const poolRef = useRef<THREE.InstancedMesh>(null);

  const sunUtcMs = useCampusStore((s) => s.sunUtcMs);
  const night = useCampusStore((s) => s.night);
  const glow = Math.max(night ? 1 : 0, nightFactor(getSunInfo(sunUtcMs)));
  const invalidate = useThree((s) => s.invalidate);

  const poleGeo = useMemo(() => new THREE.CylinderGeometry(0.12, 0.18, POLE_HEIGHT, 6), []);
  const headGeo = useMemo(() => new THREE.SphereGeometry(0.5, 8, 6), []);
  const poolGeo = useMemo(() => new THREE.PlaneGeometry(16, 16).rotateX(-Math.PI / 2), []);
  const texture = useMemo(glowTexture, []);
  const poleMat = useMemo(
    () => new THREE.MeshStandardMaterial({ color: '#3b4452', roughness: 0.8, flatShading: true }),
    [],
  );
  const headMat = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: '#ffe9b0',
        emissive: new THREE.Color('#ffd27a'),
        emissiveIntensity: 0,
        roughness: 0.5,
      }),
    [],
  );
  const poolMat = useMemo(
    () =>
      new THREE.MeshBasicMaterial({
        color: '#ffc46b',
        map: texture ?? undefined,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        opacity: 0,
        polygonOffset: true,
        polygonOffsetFactor: -4,
        polygonOffsetUnits: -4,
      }),
    [texture],
  );
  const haloMat = useMemo(
    () =>
      new THREE.PointsMaterial({
        color: '#ffe0a0',
        map: texture ?? undefined,
        size: 18,
        sizeAttenuation: true,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        opacity: 0,
      }),
    [texture],
  );

  // One matrix per lamp for each of the three instanced meshes.
  useEffect(() => {
    const dummy = new THREE.Object3D();
    lamps.forEach((l, i) => {
      const [x, y, z] = l.position;
      const yaw = l.rotation?.[1] ?? 0;
      dummy.rotation.set(0, yaw, 0);
      dummy.scale.setScalar(l.scale ?? 1);

      dummy.position.set(x, y + POLE_HEIGHT / 2, z);
      dummy.updateMatrix();
      poleRef.current?.setMatrixAt(i, dummy.matrix);

      dummy.position.set(x, y + HEAD_HEIGHT, z);
      dummy.updateMatrix();
      headRef.current?.setMatrixAt(i, dummy.matrix);

      dummy.position.set(x, y + 0.25, z);
      dummy.updateMatrix();
      poolRef.current?.setMatrixAt(i, dummy.matrix);
    });
    for (const ref of [poleRef, headRef, poolRef]) {
      if (ref.current) ref.current.instanceMatrix.needsUpdate = true;
    }
    invalidate();
  }, [lamps, invalidate]);

  // World-sized halo at each head (points have no triangles).
  const haloGeo = useMemo(() => {
    const points: number[] = [];
    for (const l of lamps) {
      points.push(l.position[0], l.position[1] + HEAD_HEIGHT, l.position[2]);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(points, 3));
    return g;
  }, [lamps]);

  useEffect(() => {
    headMat.emissiveIntensity = 2.2 * glow;
    poolMat.opacity = 0.55 * glow;
    haloMat.opacity = 0.85 * glow;
    invalidate();
  }, [glow, headMat, poolMat, haloMat, invalidate]);

  if (lamps.length === 0) return null;

  return (
    <>
      <instancedMesh ref={poleRef} args={[poleGeo, poleMat, lamps.length]} raycast={() => null} />
      <instancedMesh ref={headRef} args={[headGeo, headMat, lamps.length]} raycast={() => null} />
      <instancedMesh
        ref={poolRef}
        args={[poolGeo, poolMat, lamps.length]}
        visible={glow > 0.02}
        raycast={() => null}
        renderOrder={2}
      />
      <points geometry={haloGeo} material={haloMat} visible={glow > 0.02} raycast={() => null} renderOrder={3} />
    </>
  );
}
