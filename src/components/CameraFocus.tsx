'use client';

import { useEffect, useRef, useState } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { loadNav } from '../lib/data';
import { useCampusStore } from '../lib/store';
import type { NavGraph } from '../lib/types';

const FOCUS_DISTANCE = 320;
const MIN_CAMERA_HEIGHT = 60;

interface FocusAnim {
  active: boolean;
  target: THREE.Vector3;
  position: THREE.Vector3;
}

/**
 * Flies the camera to a building when the store's `focus` changes.
 * Resolves the building's entrance anchor (ENTR_<osm_id>, same id mapping the
 * router uses) from nav.json and smooths both the orbit target and the camera
 * position toward it. Rendered inside the Canvas; must stay there (R3F hooks).
 */
export function CameraFocus() {
  const focus = useCampusStore((s) => s.focus);
  const camera = useThree((s) => s.camera);
  const controls = useThree((s) => s.controls) as
    | { target: THREE.Vector3; update: () => void }
    | null;
  const [nav, setNav] = useState<NavGraph | null>(null);
  const anim = useRef<FocusAnim | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadNav()
      .then((n) => {
        if (!cancelled) setNav(n);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!focus || !nav) return;
    const anchorId = focus.id.startsWith('BLDG_')
      ? `ENTR_${focus.id.slice(5)}`
      : focus.id;
    const node = nav.nodes.find((n) => n.id === anchorId);
    if (!node) return;

    const target = new THREE.Vector3(node.x, 0, node.z);
    // Keep the current viewing direction but at a fixed tour distance.
    const offset = camera.position.clone().sub(controls?.target ?? new THREE.Vector3());
    if (offset.lengthSq() < 1) offset.set(0.6, 0.8, 0.6);
    offset.setLength(FOCUS_DISTANCE);
    const position = target.clone().add(offset);
    if (position.y < MIN_CAMERA_HEIGHT) position.y = MIN_CAMERA_HEIGHT;
    anim.current = { active: true, target, position };
  }, [focus, nav, camera, controls]);

  useFrame((_, delta) => {
    const a = anim.current;
    if (!a || !a.active || !controls) return;
    const k = 1 - Math.exp(-Math.min(delta, 0.1) * 4);
    controls.target.lerp(a.target, k);
    camera.position.lerp(a.position, k);
    if (
      controls.target.distanceTo(a.target) < 0.5 &&
      camera.position.distanceTo(a.position) < 0.5
    ) {
      a.active = false;
      controls.update();
    }
  });

  return null;
}
