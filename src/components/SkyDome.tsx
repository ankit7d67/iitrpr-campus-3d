'use client';

import { Stars } from '@react-three/drei';
import { useEffect, useMemo } from 'react';
import { Color, ShaderMaterial } from 'three';
import { Sky } from 'three/examples/jsm/objects/Sky.js';
import { getSunInfo, nightFactor } from '../lib/sun';
import { useCampusStore } from '../lib/store';

const DAY_HAZE = new Color('#bcd4e6');
const NIGHT_HAZE = new Color('#0b1426');

/**
 * Phase 7 item 7-8: physical (Preetham) sky dome, horizon fog, stars and moon.
 *
 * No textures or GLB geometry are added — the sky is three.js's procedural
 * Sky shader, positioned from the SAME solar model that drives the scene key
 * light (7-7). `nightFactor()` fades the haze and switches on the stars/moon
 * over civil twilight, matching the street lamps in `StreetLamps.tsx`.
 */
export function SkyDome() {
  const sunUtcMs = useCampusStore((s) => s.sunUtcMs);
  const info = getSunInfo(sunUtcMs);
  const dark = nightFactor(info);

  const sky = useMemo(() => {
    const s = new Sky();
    s.scale.setScalar(12000);
    s.frustumCulled = false;
    s.renderOrder = -1; // behind everything; it sits at the far plane anyway
    s.raycast = () => null;
    return s;
  }, []);

  // Point the sky's sun at the computed azimuth/elevation. Below the horizon
  // the shader is clamped to 2°: the darkening itself comes from `nightFactor`
  // (haze + stars/moon), which keeps the twilight colours stable.
  useEffect(() => {
    const uniforms = (sky.material as ShaderMaterial).uniforms;
    const el = (Math.max(info.elevationDeg, 2) * Math.PI) / 180;
    const az = (info.azimuthDeg * Math.PI) / 180;
    uniforms.sunPosition.value.set(
      Math.cos(el) * Math.sin(az),
      Math.sin(el),
      -Math.cos(el) * Math.cos(az), // scene axes: x = east, y = up, z = −north
    );
    uniforms.turbidity.value = 2 + 4 * dark;
    uniforms.rayleigh.value = 0.8 + 1.2 * dark;
    uniforms.mieCoefficient.value = 0.005;
    uniforms.mieDirectionalG.value = 0.85;
  }, [sky, info.elevationDeg, info.azimuthDeg, dark]);

  const haze = useMemo(() => DAY_HAZE.clone().lerp(NIGHT_HAZE, dark).getStyle(), [dark]);

  // The moon sits opposite the sun: high in the sky when the sun is well below
  // the horizon. It is a plain unlit sphere — no texture, no extra light.
  const moonPosition = useMemo<[number, number, number]>(() => {
    const el = (Math.max(15, -info.elevationDeg) * Math.PI) / 180;
    const az = ((info.azimuthDeg + 180) % 360) * (Math.PI / 180);
    const r = 3000;
    return [Math.cos(el) * Math.sin(az) * r, Math.sin(el) * r, -Math.cos(el) * Math.cos(az) * r];
  }, [info.elevationDeg, info.azimuthDeg]);

  return (
    <>
      <color attach="background" args={[haze]} />
      <primitive object={sky} />
      <fog attach="fog" args={[haze, 900, 6500]} />
      {dark > 0.25 ? (
        <Stars radius={1500} depth={200} count={3000} factor={6} saturation={0} fade speed={0} />
      ) : null}
      {dark > 0.4 ? (
        <mesh position={moonPosition} raycast={() => null}>
          <sphereGeometry args={[26, 16, 12]} />
          <meshBasicMaterial color="#f3efdc" fog={false} transparent opacity={dark * 0.9} />
        </mesh>
      ) : null}
    </>
  );
}
