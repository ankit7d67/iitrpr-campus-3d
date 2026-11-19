'use client';

import { Bloom, EffectComposer } from '@react-three/postprocessing';
import { useThree } from '@react-three/fiber';
import { BlendFunction, Effect } from 'postprocessing';
import { useEffect, useMemo } from 'react';
import { HalfFloatType, Uniform, Vector3 } from 'three';

// Phase 7 item 7-14: finishing pass — ACES filmic tone mapping (the composer
// disables the renderer's own), gentle contrast, a slightly warm tint, darker
// corners and very faint static grain. Kept identical to the reference grade;
// only the parameters are driven by this app's time-of-day model.
const GRADE = /* glsl */ `
uniform float exposure;
uniform float contrast;
uniform vec3 tint;
uniform float vignette;
uniform float grain;

vec3 rrtOdtFit(vec3 v) {
  vec3 a = v * (v + 0.0245786) - 0.000090537;
  vec3 b = v * (0.983729 * v + 0.4329510) + 0.238081;
  return a / b;
}
vec3 aces(vec3 color) {
  const mat3 inMat = mat3(0.59719, 0.07600, 0.02840, 0.35458, 0.90834, 0.13383, 0.04823, 0.01566, 0.83777);
  const mat3 outMat = mat3(1.60475, -0.10208, -0.00327, -0.53108, 1.10813, -0.07276, -0.07367, -0.00605, 1.07602);
  color *= exposure / 0.6;
  return clamp(outMat * rrtOdtFit(inMat * color), 0.0, 1.0);
}

void mainImage(const in vec4 inputColor, const in vec2 uv, out vec4 outputColor) {
  vec3 c = aces(inputColor.rgb);
  vec3 s = sqrt(c); // contrast in roughly perceptual space
  s = clamp((s - 0.5) * (1.0 + contrast) + 0.5, 0.0, 1.0);
  c = s * s * tint;
  c *= 1.0 - vignette * smoothstep(0.35, 0.9, distance(uv, vec2(0.5)) * 1.2);
  float n = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453) - 0.5;
  c += n * grain;
  outputColor = vec4(c, inputColor.a);
}
`;

class GradeEffect extends Effect {
  constructor() {
    super('GradeEffect', GRADE, {
      blendFunction: BlendFunction.SET,
      uniforms: new Map<string, Uniform>([
        ['exposure', new Uniform(1)],
        ['contrast', new Uniform(0.08)],
        ['tint', new Uniform(new Vector3(1.02, 1.0, 0.97))],
        ['vignette', new Uniform(0.28)],
        ['grain', new Uniform(0.012)],
      ]),
    });
  }
}

/** Bloom + colour grade; nightGlow 0..1 comes from the shared solar model. */
export function Effects({ nightGlow }: { nightGlow: number }) {
  const invalidate = useThree((s) => s.invalidate);
  const grade = useMemo(() => new GradeEffect(), []);
  useEffect(() => () => grade.dispose(), [grade]);

  useEffect(() => {
    // Brighter at dusk/night, as in the reference lighting model.
    grade.uniforms.get('exposure')!.value = 1 + 0.3 * nightGlow;
    invalidate();
  }, [grade, nightGlow, invalidate]);

  // By day only very bright things bloom; at night the lit windows and lamps do.
  const threshold = 0.95 - 0.6 * nightGlow;
  const intensity = 0.2 + 0.5 * nightGlow;
  return (
    <EffectComposer multisampling={4} frameBufferType={HalfFloatType}>
      <Bloom mipmapBlur luminanceThreshold={threshold} luminanceSmoothing={0.2} intensity={intensity} radius={0.7} />
      <primitive object={grade} />
    </EffectComposer>
  );
}
