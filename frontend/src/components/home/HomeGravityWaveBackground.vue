<script setup lang="ts">
import { onActivated, onBeforeUnmount, onDeactivated, onMounted, ref } from 'vue'
import * as THREE from 'three'

const hostRef = ref<HTMLDivElement | null>(null)

let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let geometry: THREE.BufferGeometry | null = null
let material: THREE.ShaderMaterial | null = null
let particles: THREE.Points | null = null
let animationFrameId = 0
let isAnimating = false

const radius = 60
const step = 4

function buildPointPositions() {
  const positions: number[] = []
  for (let x = -radius; x <= radius; x += step) {
    for (let z = -radius; z <= radius; z += step) {
      if (x * x + z * z <= radius * radius) {
        positions.push(x, 0, z)
      }
    }
  }
  return positions
}

function resize() {
  if (!renderer || !camera) return
  const host = hostRef.value
  const width = host?.clientWidth || window.innerWidth
  const height = host?.clientHeight || window.innerHeight
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height, false)
}

function animate(time: number) {
  if (!isAnimating || !renderer || !scene || !camera || !material) return
  material.uniforms.uTime.value = time * 0.001
  renderer.render(scene, camera)
  animationFrameId = requestAnimationFrame(animate)
}

function startAnimation() {
  if (!renderer || isAnimating) return
  isAnimating = true
  resize()
  window.addEventListener('resize', resize)
  animationFrameId = requestAnimationFrame(animate)
}

function stopAnimation() {
  if (!isAnimating) return
  isAnimating = false
  window.removeEventListener('resize', resize)
  cancelAnimationFrame(animationFrameId)
  animationFrameId = 0
}

onMounted(() => {
  const host = hostRef.value
  if (!host) return

  scene = new THREE.Scene()

  camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000)
  camera.position.set(0, 15, 35)

  renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: true,
    powerPreference: 'high-performance',
  })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  host.appendChild(renderer.domElement)

  geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(buildPointPositions(), 3))

  material = new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uColorInner: { value: new THREE.Color('#66aaff') },
      uColorOuter: { value: new THREE.Color('#99eeff') },
      uRadius: { value: radius },
    },
    vertexShader: `
      uniform float uTime;
      varying float vElevation;
      varying float vDist;

      void main() {
        vec3 pos = position;
        float dist = length(pos.xz);
        vDist = dist;

        float activeWave = sin(dist * 0.2 - uTime * 1.0) * 4.0;
        float decay = exp(-dist * 0.015);
        activeWave *= decay;
        pos.y += activeWave;
        vElevation = pos.y;

        vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
        gl_Position = projectionMatrix * mvPosition;
        gl_PointSize = (400.0 / -mvPosition.z);
      }
    `,
    fragmentShader: `
      uniform vec3 uColorInner;
      uniform vec3 uColorOuter;
      uniform float uRadius;

      varying float vElevation;
      varying float vDist;

      void main() {
        float ptDist = distance(gl_PointCoord, vec2(0.5));
        if (ptDist > 0.5) discard;

        float mixVal = (vDist / uRadius) + (vElevation * 0.2);
        vec3 color = mix(uColorInner, uColorOuter, clamp(mixVal, 0.0, 1.0));
        float edgeFade = smoothstep(uRadius, uRadius - 15.0, vDist);
        float alpha = smoothstep(0.5, 0.4, ptDist) * edgeFade * 0.65;
        gl_FragColor = vec4(color, alpha);
      }
    `,
    transparent: true,
    depthWrite: false,
  })

  particles = new THREE.Points(geometry, material)
  particles.rotation.x = 0.4
  particles.rotation.z = -0.3
  scene.add(particles)

  startAnimation()
})

onActivated(() => {
  startAnimation()
})

onDeactivated(() => {
  stopAnimation()
})

onBeforeUnmount(() => {
  stopAnimation()

  if (scene && particles) {
    scene.remove(particles)
  }

  geometry?.dispose()
  material?.dispose()

  if (renderer) {
    renderer.dispose()
    renderer.domElement.remove()
  }

  particles = null
  geometry = null
  material = null
  camera = null
  scene = null
  renderer = null
})
</script>

<template>
  <div ref="hostRef" class="home-gravity-wave-bg" aria-hidden="true"></div>
</template>

<style scoped>
.home-gravity-wave-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.home-gravity-wave-bg :deep(canvas) {
  width: 100%;
  height: 100%;
  display: block;
}
</style>
