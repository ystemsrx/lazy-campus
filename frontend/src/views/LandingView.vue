<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as THREE from 'three'
import HomeGravityWaveBackground from '../components/home/HomeGravityWaveBackground.vue'

const router = useRouter()
const canvasRef = ref<HTMLCanvasElement | null>(null)
const isIntroFinished = ref(false)
const introPhase = ref(0)
const showBtnText = ref(false)
const introVisible = ref(false)
const introMotionReady = ref(false)
const appTitle = import.meta.env.VITE_APP_TITLE || '校园任务平台'

let animationFrameId = 0
let renderer: THREE.WebGLRenderer | null = null

function navigateToLogin() {
  router.push('/login')
}

function navigateToHome() {
  router.push('/home')
}

onMounted(() => {
  const canvas = canvasRef.value
  if (!canvas) return

  // === Scene setup ===
  const scene = new THREE.Scene()
  scene.fog = new THREE.Fog(0xffffff, 12, 35)

  const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100)
  camera.position.z = 10

  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
  renderer.setSize(window.innerWidth, window.innerHeight)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap

  // === Create paperclip geometry (same as demo) ===
  const points: THREE.Vector3[] = []

  const pushLine = (x1: number, y1: number, x2: number, y2: number) => {
    const steps = 15
    const startI = points.length === 0 ? 0 : 1
    for (let i = startI; i <= steps; i++) {
      points.push(new THREE.Vector3(
        x1 + (x2 - x1) * (i / steps),
        y1 + (y2 - y1) * (i / steps),
        0
      ))
    }
  }

  const pushArc = (cx: number, cy: number, r: number, startAngle: number, endAngle: number) => {
    const steps = 25
    for (let i = 1; i <= steps; i++) {
      const a = startAngle + (endAngle - startAngle) * (i / steps)
      points.push(new THREE.Vector3(cx + r * Math.cos(a), cy + r * Math.sin(a), 0))
    }
  }

  pushLine(0.2, -0.5, 0.2, 1.0)
  pushArc(0.0, 1.0, 0.2, 0, Math.PI)
  pushLine(-0.2, 1.0, -0.2, -1.2)
  pushArc(0.1, -1.2, 0.3, Math.PI, Math.PI * 2)
  pushLine(0.4, -1.2, 0.4, 1.2)
  pushArc(0.0, 1.2, 0.4, 0, Math.PI)
  pushLine(-0.4, 1.2, -0.4, -0.8)

  const curve = new THREE.CatmullRomCurve3(points)
  const geometry = new THREE.TubeGeometry(curve, 250, 0.08, 32, false)

  const material = new THREE.MeshStandardMaterial({
    color: 0xe2e8f0,
    metalness: 0.85,
    roughness: 0.15,
    envMapIntensity: 1.5
  })

  const paperclip = new THREE.Mesh(geometry, material)
  paperclip.castShadow = true
  paperclip.receiveShadow = true
  scene.add(paperclip)

  // === Lighting ===
  const hemiLight = new THREE.HemisphereLight(0xffffff, 0x94a3b8, 0.6)
  scene.add(hemiLight)

  const dirLight1 = new THREE.DirectionalLight(0xffffff, 1.2)
  dirLight1.position.set(5, 10, 7)
  dirLight1.castShadow = true
  scene.add(dirLight1)

  const dirLight2 = new THREE.DirectionalLight(0xe0e7ff, 0.8)
  dirLight2.position.set(-10, -5, 5)
  scene.add(dirLight2)

  const dirLight3 = new THREE.DirectionalLight(0xffffff, 1)
  dirLight3.position.set(0, 5, -5)
  scene.add(dirLight3)

  // === Scroll animation state ===
  let currentProgress = 0
  let targetProgress = 0

  const body = document.body
  const originalHeight = body.style.height
  const originalOverflow = body.style.overflowX

  let isMobile = window.innerWidth < 768
  // On desktop, force 400vh to drive scroll-parallax; on mobile, let content determine height
  if (!isMobile) {
    body.style.height = '400vh'
  }

  // Positions
  const clipStartPos = new THREE.Vector3(isMobile ? 1.5 : 3.5, 2.5, 3)
  const clipStartRot = new THREE.Vector3(0.3, -0.4, -Math.PI / 4)
  const clipStartScale = isMobile ? 1.5 : 2.5

  const introStartPos = clipStartPos.clone().add(new THREE.Vector3(2, 4, 0))

  // On mobile, paperclip ends at top-left corner and shrinks slightly
  const clipEndPos = new THREE.Vector3(isMobile ? -1.5 : 0, isMobile ? 2.5 : 0, isMobile ? 3 : 0)
  const clipEndRot = new THREE.Vector3(0, Math.PI * 2, isMobile ? Math.PI / 4 : -Math.PI / 6)
  const clipEndScale = isMobile ? 1.1 : 1.1

  let introStartTime = 0
  let localIntroPhase = 0
  let localIsIntroFinished = false

  // Text elements
  const textLeftEl = document.getElementById('landing-text-left')
  const textRightEl = document.getElementById('landing-text-right')
  const btnLeftEl = document.getElementById('landing-btn-left')
  const introContainerEl = document.getElementById('landing-intro-container')
  const scrollHintEl = document.getElementById('landing-scroll-hint')
  const textAgentEl = document.getElementById('landing-text-agent')
  const titleLineEls = Array.from(document.querySelectorAll<HTMLElement>('.landing-title-line'))

  const updateTitleLineOffsets = () => {
    if (titleLineEls.length === 0) return
    const widths = titleLineEls.map((el) => el.getBoundingClientRect().width)
    const maxWidth = Math.max(...widths)
    if (introContainerEl) {
      introContainerEl.style.setProperty('--landing-title-width', `${maxWidth}px`)
    }
    titleLineEls.forEach((el, index) => {
      const offset = (maxWidth - widths[index]) / 2
      el.style.setProperty('--landing-line-center-offset', `${offset}px`)
    })
  }

  // Button elements for scroll-driven animation
  const btnEl = document.getElementById('landing-explore-btn') as HTMLElement | null
  const btnLabelEl = btnEl?.querySelector('.landing-btn-label') as HTMLElement | null
  const getExpandedBtnWidth = (): number => {
    if (!btnEl) return window.innerWidth < 768 ? 200 : 230
    const widthVar = getComputedStyle(btnEl).getPropertyValue('--landing-btn-expanded-width').trim()
    const parsed = Number.parseFloat(widthVar)
    if (Number.isFinite(parsed) && parsed > 56) return parsed
    return window.innerWidth < 768 ? 200 : 230
  }
  let fullBtnWidth = getExpandedBtnWidth()
  let hasActivatedScrollBtnAnimation = false

  function lerp(start: number, end: number, t: number): number {
    return start * (1 - t) + end * t
  }

  function easeInOutSine(x: number): number {
    return -(Math.cos(Math.PI * x) - 1) / 2
  }

  const onScroll = () => {
    const maxScroll = document.body.scrollHeight - window.innerHeight
    targetProgress = Math.max(0, Math.min(1, window.scrollY / maxScroll))
  }

  window.addEventListener('scroll', onScroll)

  const resetParallaxStyles = () => {
    if (textLeftEl) {
      textLeftEl.style.transform = ''
      textLeftEl.style.opacity = ''
    }
    if (textRightEl) {
      textRightEl.style.transform = ''
      textRightEl.style.opacity = ''
    }
    if (btnLeftEl) {
      btnLeftEl.style.transform = ''
      btnLeftEl.style.opacity = ''
      btnLeftEl.style.pointerEvents = ''
    }
    if (textAgentEl) {
      textAgentEl.style.transform = ''
      textAgentEl.style.opacity = ''
    }
  }

  function animate(time: number) {
    animationFrameId = requestAnimationFrame(animate)

    const floatTime = time * 0.001
    const floatY = Math.sin(floatTime * 1.5) * 0.08
    const floatRotX = Math.sin(floatTime * 0.8) * 0.03
    const floatRotY = Math.cos(floatTime * 0.5) * 0.05

    // === Phase A: Intro animation ===
    if (!localIsIntroFinished) {
      if (introStartTime === 0) introStartTime = time
      const elapsed = time - introStartTime

      // Phase 1: Text slides left, paperclip enters
      if (elapsed > 500 && localIntroPhase === 0) {
        localIntroPhase = 1
        introPhase.value = 1
      }

      // Phase 2: Button pops in
      if (elapsed > 1500 && localIntroPhase === 1) {
        localIntroPhase = 2
        introPhase.value = 2
      }

      // Phase 3: Button stretches into capsule
      if (elapsed > 2100 && localIntroPhase === 2) {
        localIntroPhase = 3
        introPhase.value = 3
        setTimeout(() => { showBtnText.value = true }, 250)
      }

      // Phase 4: Intro finished, unlock scroll
      if (elapsed > 3000 && localIntroPhase === 3) {
        localIntroPhase = 4
        introPhase.value = 4
        localIsIntroFinished = true
        isIntroFinished.value = true
        fullBtnWidth = getExpandedBtnWidth()
      }

      // Paperclip entrance
      if (localIntroPhase >= 1) {
        const progress = Math.min((elapsed - 500) / 1000, 1)
        const easeP = 1 - Math.pow(1 - progress, 3)
        paperclip.position.lerpVectors(introStartPos, clipStartPos, easeP)
      } else {
        paperclip.position.copy(introStartPos)
      }

      paperclip.rotation.set(clipStartRot.x, clipStartRot.y, clipStartRot.z)
      paperclip.scale.set(clipStartScale, clipStartScale, clipStartScale)
      paperclip.position.y += floatY
      paperclip.rotation.x += floatRotX
      paperclip.rotation.y += floatRotY

    } else {
      // === Phase B: Scroll animation ===
      currentProgress += (targetProgress - currentProgress) * 0.08

      paperclip.position.lerpVectors(clipStartPos, clipEndPos, currentProgress)

      const rotP = easeInOutSine(currentProgress)
      paperclip.rotation.x = lerp(clipStartRot.x, clipEndRot.x, rotP)
      paperclip.rotation.y = lerp(clipStartRot.y, clipEndRot.y, rotP)
      paperclip.rotation.z = lerp(clipStartRot.z, clipEndRot.z, rotP)

      const scale = lerp(clipStartScale, clipEndScale, currentProgress)
      paperclip.scale.set(scale, scale, scale)

      paperclip.position.y += floatY
      paperclip.rotation.x += floatRotX
      paperclip.rotation.y += floatRotY

      // Fade out intro container during first 30% of scroll
      if (introContainerEl) {
        const introFade = Math.min(1, currentProgress / 0.15)
        introContainerEl.style.opacity = String(1 - introFade)
        if (isMobile) {
          introContainerEl.style.transform = `translateY(-${introFade * 8}vh)`
        } else {
          introContainerEl.style.transform = `translate(0, calc(-50% - ${introFade * 8}vh))`
        }
        introContainerEl.style.pointerEvents = introFade > 0.5 ? 'none' : 'auto'
      }

      // Explore button: left edge slides right, right edge stays fixed
      if (btnEl) {
        const btnP = Math.min(1, currentProgress / 0.12)

        // Keep intro expansion controlled by CSS transition.
        if (btnP <= 0.001 && !hasActivatedScrollBtnAnimation) {
          btnEl.style.width = `${fullBtnWidth}px`
          btnEl.style.marginLeft = '0px'
          btnEl.style.opacity = '1'
          btnEl.style.pointerEvents = 'auto'
          if (btnLabelEl) {
            btnLabelEl.style.opacity = showBtnText.value ? '1' : '0'
          }
        } else if (!hasActivatedScrollBtnAnimation) {
          hasActivatedScrollBtnAnimation = true
          btnEl.style.transition = 'box-shadow 250ms ease, background 250ms ease'
        }

        // Phase 1 (0–80%): shrink width from full → 56px (circle)
        const shrinkP = Math.min(1, btnP / 0.8)
        const easedShrink = 1 - Math.pow(1 - shrinkP, 2.5)
        const minW = 56 // Same as height → perfect circle
        const curW = fullBtnWidth - (fullBtnWidth - minW) * easedShrink

        // Phase 2 (80–100%): fade out the circle
        const fadeP = Math.max(0, (btnP - 0.8) / 0.2)

        // Pin the right edge: shift button right as it shrinks
        const shift = fullBtnWidth - curW
        btnEl.style.width = `${curW}px`
        btnEl.style.marginLeft = `${shift}px`
        btnEl.style.opacity = String(1 - fadeP)
        btnEl.style.pointerEvents = fadeP > 0.3 ? 'none' : 'auto'

        // Label fades in the first 30% of shrink
        if (btnLabelEl) {
          btnLabelEl.style.opacity = String(Math.max(0, 1 - shrinkP * 3))
        }

        // Circle stays at left:4px inside button — moves right on screen with the button
      }

      // Hide scroll hint on any scroll
      if (scrollHintEl) {
        scrollHintEl.style.opacity = currentProgress > 0.02 ? '0' : '1'
      }

      if (!isMobile) {
        // Text parallax
        const textProgress = Math.min(1, currentProgress / 0.85)
        const p = 1 - Math.pow(1 - textProgress, 3)
        const trackY = 85 - p * 85

        if (textLeftEl) {
          const leftY = 15 + trackY
          textLeftEl.style.transform = `translateY(${leftY}vh)`
          textLeftEl.style.opacity = String(1 - (trackY / 85))
        }

        if (textRightEl) {
          const rightY = Math.min(50, trackY)
          textRightEl.style.transform = `translateY(${rightY}vh)`
          textRightEl.style.opacity = String(1 - (rightY / 50))
        }

        if (btnLeftEl) {
          const rightY = Math.min(50, trackY)
          btnLeftEl.style.transform = `translateY(${rightY}vh)`
          btnLeftEl.style.opacity = String(1 - (rightY / 50))
          btnLeftEl.style.pointerEvents = rightY < 49 ? 'auto' : 'none'
        }

        // Agent text parallax (appears slightly later, center-right)
        if (textAgentEl) {
          const agentProgress = Math.max(0, Math.min(1, (currentProgress - 0.15) / 0.7))
          const ap = 1 - Math.pow(1 - agentProgress, 3)
          const agentY = 60 - ap * 60
          textAgentEl.style.transform = `translateY(${agentY}vh)`
          textAgentEl.style.opacity = String(Math.min(1, ap * 1.5))
        }
      }

      // Mobile: update clip end position dynamically (top-left corner)
      if (isMobile) {
        clipEndPos.set(-1.5, 2.5, 3)
      } else {
        clipEndPos.set(0, 0, 0)
      }
    }

    renderer!.render(scene, camera)
  }

  animationFrameId = requestAnimationFrame(animate)

  const onResize = () => {
    const nextIsMobile = window.innerWidth < 768
    if (nextIsMobile !== isMobile) {
      isMobile = nextIsMobile
      if (isMobile) {
        resetParallaxStyles()
        body.style.height = '' // let content determine height on mobile
      } else {
        body.style.height = '400vh'
      }
    }

    camera.aspect = window.innerWidth / window.innerHeight
    camera.updateProjectionMatrix()
    renderer!.setSize(window.innerWidth, window.innerHeight)
    fullBtnWidth = getExpandedBtnWidth()
    updateTitleLineOffsets()

    if (window.innerWidth < 768) {
      clipStartPos.set(1.5, 2.5, 3)
      clipEndPos.set(-1.5, 2.5, 3)
      clipEndRot.z = Math.PI / 4
    } else {
      clipStartPos.set(3.5, 2.5, 3)
      clipEndPos.set(0, 0, 0)
      clipEndRot.z = -Math.PI / 6
    }
    introStartPos.copy(clipStartPos).add(new THREE.Vector3(2, 4, 0))
  }

  window.addEventListener('resize', onResize)

  requestAnimationFrame(() => {
    updateTitleLineOffsets()
    introVisible.value = true
    requestAnimationFrame(() => {
      introMotionReady.value = true
    })
  })
  if ('fonts' in document && document.fonts?.ready) {
    document.fonts.ready.then(updateTitleLineOffsets).catch(() => undefined)
  }

  // Cleanup on unmount
  onBeforeUnmount(() => {
    cancelAnimationFrame(animationFrameId)
    window.removeEventListener('scroll', onScroll)
    window.removeEventListener('resize', onResize)
    body.style.height = originalHeight
    body.style.overflowX = originalOverflow
    window.scrollTo(0, 0)
    renderer?.dispose()
    renderer = null
  })
})

function scrollToExplore() {
  const startY = window.scrollY
  const endY = document.body.scrollHeight - window.innerHeight
  const distance = endY - startY
  const duration = 2500
  let startTime: number | null = null

  function scrollAnim(currentTime: number) {
    if (startTime === null) startTime = currentTime
    const timeElapsed = currentTime - startTime
    const progress = Math.min(timeElapsed / duration, 1)
    const ease = progress < 0.5
      ? 4 * Math.pow(progress, 3)
      : 1 - Math.pow(-2 * progress + 2, 3) / 2
    window.scrollTo(0, startY + distance * ease)
    if (timeElapsed < duration) {
      requestAnimationFrame(scrollAnim)
    }
  }
  requestAnimationFrame(scrollAnim)
}


</script>

<template>
  <div class="landing-root" :class="{ 'landing-locked': !isIntroFinished }">
    <HomeGravityWaveBackground class="landing-wave-bg" />
    <!-- Three.js Canvas -->
    <canvas ref="canvasRef" class="landing-canvas"></canvas>

    <!-- Intro container: title + CTA -->
    <div
      id="landing-intro-container"
      class="landing-intro"
      :class="[
        introPhase >= 1 ? 'landing-intro--left' : 'landing-intro--center',
        introVisible ? 'landing-intro--visible' : 'landing-intro--hidden',
        introMotionReady ? 'landing-intro--motion' : ''
      ]"
    >
      <div class="landing-intro-inner">
        <h1
          class="landing-title"
          :class="introPhase >= 1 ? 'landing-title--left' : 'landing-title--center'"
        >
          <span class="landing-title-line">连接</span>
          <span class="landing-title-line">校园的每一个</span>
          <span class="landing-title-line landing-title-accent">可能</span>
        </h1>

        <!-- CTA Button -->
        <div
          class="landing-btn-wrapper"
          :class="introPhase >= 2 ? 'landing-btn-wrapper--visible' : ''"
        >
          <button
            id="landing-explore-btn"
            class="landing-btn"
            :class="introPhase >= 3 ? 'landing-btn--expanded' : ''"
            @click="scrollToExplore"
          >
            <div class="landing-btn-circle">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </div>
            <span class="landing-btn-label" :class="showBtnText ? 'landing-btn-label--visible' : ''">
              探索 {{ appTitle }}
            </span>
          </button>
        </div>

        <!-- Hero sub-content: subtitle + feature chips -->
        <div class="landing-hero-sub" :class="{ 'landing-hero-sub--visible': isIntroFinished }">
          <p class="landing-subtitle">一站式校园互助平台，让每一份需求都被看见</p>
          <div class="landing-feature-row">
            <div class="landing-feature-chip" style="transition-delay: 150ms">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
              <span>极速发布</span>
            </div>
            <div class="landing-feature-chip" style="transition-delay: 300ms">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
              <span>安全互评</span>
            </div>
            <div class="landing-feature-chip" style="transition-delay: 450ms">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/></svg>
              <span>AI 赋能</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Scroll hint -->
    <div id="landing-scroll-hint" class="landing-scroll-hint" :class="isIntroFinished ? 'landing-scroll-hint--visible' : ''">
      <span>向下滚动</span>
      <svg class="landing-scroll-arrow" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 14l-7 7m0 0l-7-7m7 7V3" />
      </svg>
    </div>

    <!-- Parallax text: left -->
    <div id="landing-text-left" class="landing-parallax-text landing-parallax-text--left">
      <h2 class="landing-parallax-title">发布你的<br/>校园委托</h2>
      <p class="landing-parallax-desc">
        无论是跑腿代拿、学习互助，还是技能交换，
        一键发布，让校园里的伙伴来帮你。
      </p>
    </div>

    <!-- Parallax text: right -->
    <div id="landing-text-right" class="landing-parallax-text landing-parallax-text--right">
      <h2 class="landing-parallax-title">高效<br/>安心可靠</h2>
      <p class="landing-parallax-desc">
        双向互评、信誉沉淀、隐私保护——
        构建值得信赖的校园互助社区。
      </p>
    </div>

    <!-- AI Agent feature badge -->
    <div id="landing-text-agent" class="landing-parallax-text landing-parallax-text--agent">
      <div class="landing-agent-badge">
        <span class="landing-agent-badge-dot"></span>
        AI Agent
      </div>
      <h2 class="landing-parallax-title landing-parallax-title--agent">智能代理<br/>为你工作</h2>
      <p class="landing-parallax-desc">
        内置经过精心设计的 AI Agent，它运行在我们的定制化系统，针对上百个专业领域进行独立优化，可完整且高质量交付成果。
        一键自动执行任务——编写代码、搜索资料、生成报告文件等。
      </p>
    </div>

    <!-- CTA at bottom -->
    <div id="landing-btn-left" class="landing-bottom-cta">
      <button class="landing-pill-btn" @click="navigateToLogin">
        <div class="landing-pill-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 19L19 5M19 5v10M19 5H9" />
          </svg>
        </div>
        <span>立即登录</span>
      </button>
      <button class="landing-pill-btn landing-pill-btn--outline" @click="navigateToHome">
        <div class="landing-pill-icon landing-pill-icon--outline">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
          </svg>
        </div>
        <span>浏览大厅</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
/* ============================================
   Landing Page — LaZy Link
   ============================================ */

.landing-root {
  position: relative;
  min-height: 100vh;
  background: #f0f4f8;
  overflow-x: hidden;
}

.landing-locked {
  overflow: hidden;
  height: 100vh;
}

.landing-wave-bg {
  position: fixed !important;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

/* --- Canvas --- */
.landing-canvas {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
}

/* --- Intro container (title + button) --- */
.landing-intro {
  position: fixed;
  z-index: 20;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  transition: all 1000ms cubic-bezier(0.25, 1, 0.5, 1);
}

.landing-intro-inner {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  transition: none;
  will-change: transform;
}

.landing-intro--hidden {
  visibility: hidden;
  pointer-events: none;
}

.landing-intro--motion .landing-intro-inner {
  transition: transform 1000ms cubic-bezier(0.25, 1, 0.5, 1);
}

.landing-intro--center {
  top: 30vh;
  left: 50%;
  transform: translate(-50%, -50%);
}

.landing-intro--left {
  top: 30vh;
  left: 1.5rem;
  transform: translate(0, -50%);
}

@media (min-width: 768px) {
  .landing-intro--left {
    left: 4rem;
  }
}

/* --- Title --- */
.landing-title {
  font-size: clamp(2.8rem, 7vw, 4.5rem);
  font-weight: 900;
  line-height: 1.08;
  letter-spacing: -0.03em;
  color: #0f172a;
  display: flex;
  flex-direction: column;
  width: max-content;
  transition: all 1000ms cubic-bezier(0.25, 1, 0.5, 1);
  align-items: flex-start;
  text-align: left;
}

.landing-title--center {
  align-items: flex-start;
  text-align: left;
}

.landing-title--left {
  align-items: flex-start;
  text-align: left;
}

.landing-title-line {
  display: block;
  transition: none;
  will-change: transform;
}

.landing-intro--motion .landing-title-line {
  transition: transform 1000ms cubic-bezier(0.25, 1, 0.5, 1);
}

.landing-title--center .landing-title-line {
  transform: translateX(var(--landing-line-center-offset, 0px));
}

.landing-title--left .landing-title-line {
  transform: translateX(0);
}

.landing-title-accent {
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* --- CTA button wrapper --- */
.landing-btn-wrapper {
  width: 100%;
  display: flex;
  justify-content: flex-start;
  opacity: 0;
  transform: scale(0.5);
  transition: opacity 700ms cubic-bezier(0.34, 1.56, 0.64, 1),
              transform 700ms cubic-bezier(0.34, 1.56, 0.64, 1);
  margin-top: 2.5rem;
  transform-origin: left center;
}

.landing-btn-wrapper--visible {
  opacity: 1;
  transform: scale(1);
}

/* --- CTA button body (scroll-driven shrink) --- */
.landing-btn {
  --landing-btn-expanded-width: 210px;
  position: relative;
  display: flex;
  align-items: center;
  background: #0f172a;
  border-radius: 9999px;
  height: 56px;
  width: 56px;
  border: none;
  cursor: pointer;
  overflow: hidden;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
  /* Width transition only for intro expand; scroll animation uses inline styles */
  transition: width 700ms cubic-bezier(0.16, 1, 0.3, 1),
              box-shadow 250ms ease,
              background 250ms ease;
}

.landing-btn:hover {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
  background: #1e293b;
}

.landing-btn--expanded {
  width: var(--landing-btn-expanded-width);
}

@media (min-width: 768px) {
  .landing-btn {
    --landing-btn-expanded-width: 230px;
  }
}

/* Circle: absolute positioned so JS can drive `left` per frame */
.landing-btn-circle {
  position: absolute;
  left: 4px;
  top: 4px;
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  background: #ffffff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  color: #0f172a;
  /* No transition — driven by JS requestAnimationFrame */
}

.landing-btn-label {
  color: #ffffff;
  font-weight: 500;
  font-size: 1.05rem;
  white-space: nowrap;
  opacity: 0;
  /* Center text in the black area between circle right edge and capsule right edge */
  margin-left: 52px; /* circle left:4 + width:48 */
  flex: 1;
  text-align: center;
  font-family: var(--font-sans);
  /* No transition on opacity — JS drives it per frame */
}

.landing-btn-label--visible {
  opacity: 1;
}

/* --- Hero sub-content (subtitle + features) --- */
.landing-hero-sub {
  margin-top: 2.2rem;
  opacity: 0;
  transform: translateY(16px);
  transition: opacity 800ms cubic-bezier(0.25, 1, 0.5, 1),
              transform 800ms cubic-bezier(0.25, 1, 0.5, 1);
}

.landing-hero-sub--visible {
  opacity: 1;
  transform: translateY(0);
}

.landing-subtitle {
  font-size: 1rem;
  color: #94a3b8;
  font-weight: 300;
  letter-spacing: 0.02em;
  margin: 0 0 1.2rem 0;
  line-height: 1.6;
}

.landing-feature-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.landing-feature-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 14px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(0, 0, 0, 0.06);
  color: #475569;
  font-size: 0.82rem;
  font-weight: 500;
  letter-spacing: 0.01em;
  opacity: 0;
  transform: translateY(8px);
  transition: opacity 500ms ease, transform 500ms ease,
              background 200ms ease, box-shadow 200ms ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.landing-feature-chip svg {
  color: #8b5cf6;
  flex-shrink: 0;
}

.landing-hero-sub--visible .landing-feature-chip {
  opacity: 1;
  transform: translateY(0);
}

.landing-feature-chip:hover {
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

/* --- Scroll hint --- */
.landing-scroll-hint {
  position: fixed;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  z-index: 10;
  pointer-events: none;
  opacity: 0;
  transition: opacity 500ms ease;
  color: #94a3b8;
}

.landing-scroll-hint--visible {
  opacity: 1;
}

.landing-scroll-hint span {
  font-size: 0.8rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.landing-scroll-arrow {
  animation: landing-bounce 1.5s ease-in-out infinite;
}

@keyframes landing-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(6px); }
}

/* --- Parallax texts --- */
.landing-parallax-text {
  position: fixed;
  z-index: 10;
  width: 100%;
  max-width: 380px;
  pointer-events: none;
  opacity: 0;
}

.landing-parallax-text--left {
  left: 1.5rem;
  top: 0;
  transform: translateY(100vh);
}

.landing-parallax-text--right {
  right: 1.5rem;
  bottom: 10%;
  transform: translateY(50vh);
  text-align: right;
}

@media (min-width: 768px) {
  .landing-parallax-text--left {
    left: 4rem;
  }
  .landing-parallax-text--right {
    right: 4rem;
  }
}

.landing-parallax-title {
  font-size: clamp(2.4rem, 5vw, 3.5rem);
  font-weight: 900;
  line-height: 1.1;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.landing-parallax-desc {
  margin-top: 1rem;
  font-size: 1rem;
  line-height: 1.7;
  color: #64748b;
  font-weight: 300;
}

.landing-parallax-text--right .landing-parallax-desc {
  margin-left: auto;
}

/* --- Agent section --- */
.landing-parallax-text--agent {
  left: 0;
  right: 0;
  margin: 0 auto;
  top: 50%;
  text-align: center;
  max-width: 440px;
  padding: 0 1.5rem;
  box-sizing: border-box;
}

@media (min-width: 768px) {
  .landing-parallax-text--agent {
    left: auto;
    right: 4rem;
    margin: 0;
    top: 35%;
    text-align: left;
    padding: 0;
  }
}

.landing-agent-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 14px;
  border-radius: 9999px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(168, 85, 247, 0.12) 100%);
  color: #7c3aed;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  margin-bottom: 1rem;
  text-transform: uppercase;
}

.landing-agent-badge-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #7c3aed;
  animation: landing-pulse 2s ease-in-out infinite;
}

@keyframes landing-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

.landing-parallax-title--agent {
  background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* --- Bottom CTA buttons --- */
.landing-bottom-cta {
  position: fixed;
  left: 1.5rem;
  bottom: 10%;
  z-index: 10;
  opacity: 0;
  pointer-events: none;
  transform: translateY(50vh);
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

@media (min-width: 768px) {
  .landing-bottom-cta {
    left: 4rem;
  }
}

.landing-pill-btn {
  display: flex;
  align-items: center;
  border-radius: 9999px;
  border: 1.5px solid #0f172a;
  background: #0f172a;
  color: #ffffff;
  padding: 4px 24px 4px 4px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 0.88rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  transition: all 250ms cubic-bezier(0.16, 1, 0.3, 1);
  gap: 12px;
}

.landing-pill-btn:hover {
  background: #1e293b;
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.landing-pill-btn--outline {
  background: #ffffff;
  color: #0f172a;
}

.landing-pill-btn--outline:hover {
  background: #f8fafc;
}

.landing-pill-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #ffffff;
  color: #0f172a;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 250ms ease;
}

.landing-pill-icon--outline {
  background: #0f172a;
  color: #ffffff;
}

/* --- Mobile responsive --- */
@media (max-width: 767px) {
  .landing-root {
    padding-top: 110vh;
    padding-bottom: 40px;
  }

  .landing-intro {
    --landing-title-width: 70vw;
  }

  .landing-scroll-hint {
    display: none;
  }

  .landing-intro--center,
  .landing-intro--left {
    top: 12vh;
    left: 1.5rem;
    transform: none;
  }

  .landing-intro--center .landing-intro-inner {
    transform: translate3d(calc(50vw - 1.5rem - (var(--landing-title-width, 0px) / 2)), 0, 0);
  }

  .landing-intro--left .landing-intro-inner {
    transform: translate3d(0, 0, 0);
  }

  .landing-title--left {
    align-items: flex-start;
    text-align: left;
  }

  .landing-title--center {
    align-items: flex-start;
    text-align: left;
  }

  .landing-btn-wrapper {
    justify-content: flex-start;
    transform-origin: left center;
    margin-top: calc(50vh - 12vh - 10rem);
  }

  .landing-hero-sub {
    text-align: left;
  }

  .landing-feature-row {
    justify-content: flex-start;
  }

  .landing-title {
    font-size: 2.2rem;
  }

  .landing-btn {
    --landing-btn-expanded-width: 200px;
  }

  .landing-btn.landing-btn--shrunk {
    width: 60px;
  }

  /* Prevent parallax text overlap */
  .landing-parallax-text,
  .landing-bottom-cta {
    position: relative;
    top: auto;
    bottom: auto;
    left: auto;
    right: auto;
    transform: none;
    opacity: 1;
    pointer-events: auto;
    width: min(520px, 92vw);
    max-width: 92vw;
    margin: 0 auto 24px auto;
  }

  .landing-parallax-text {
    max-width: 92vw;
    text-align: left;
  }

  .landing-parallax-text--left {
    left: auto;
    text-align: right;
    margin-left: auto;
    margin-right: 4vw;
  }

  .landing-parallax-text--left .landing-parallax-desc {
    margin-left: auto;
  }

  .landing-parallax-text--right {
    right: auto;
    bottom: auto;
    text-align: left;
    margin-left: 4vw;
    margin-right: auto;
  }

  .landing-parallax-text--right .landing-parallax-desc {
    margin-left: 0;
  }

  .landing-parallax-title {
    font-size: 1.6rem;
  }

  .landing-parallax-desc {
    font-size: 0.85rem;
    line-height: 1.5;
  }

  /* Agent section: offset right for stagger */
  .landing-parallax-text--agent {
    left: auto;
    right: auto;
    margin: 0 auto 24px auto;
    margin-left: auto;
    margin-right: 8vw;
    top: auto;
    bottom: auto;
    max-width: 85vw;
    padding: 0;
    text-align: right;
  }

  .landing-parallax-text--agent .landing-parallax-desc {
    margin-left: auto;
  }

  .landing-parallax-title--agent {
    font-size: 1.5rem;
  }

  .landing-parallax-text--agent .landing-parallax-desc {
    font-size: 0.8rem;
    line-height: 1.5;
  }

  .landing-bottom-cta {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 10px;
    align-items: flex-start;
  }

  .landing-pill-btn {
    font-size: 0.82rem;
    padding: 3px 18px 3px 3px;
    gap: 10px;
  }

  .landing-pill-icon {
    width: 36px;
    height: 36px;
  }

  /* Feature chips responsive */
  .landing-hero-sub {
    margin-top: 1.5rem;
  }

  .landing-subtitle {
    font-size: 0.88rem;
  }

  .landing-feature-row {
    gap: 8px;
  }

  .landing-feature-chip {
    padding: 6px 11px;
    font-size: 0.76rem;
    gap: 5px;
  }

  .landing-feature-chip svg {
    width: 14px;
    height: 14px;
  }
}

/* Extra small screens */
@media (max-width: 380px) {
  .landing-title {
    font-size: 1.9rem;
  }

  .landing-btn {
    --landing-btn-expanded-width: 180px;
  }

  .landing-parallax-text {
    max-width: 50vw;
  }

  .landing-parallax-title {
    font-size: 1.4rem;
  }
}
</style>
