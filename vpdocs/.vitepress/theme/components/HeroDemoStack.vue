<script setup lang="ts">
import { ref } from 'vue'

type Slide = {
    src: string
    alt: string
}

const slides: Slide[] = [
    { src: '/demo/ui-demo.png', alt: 'ModLink Studio 主界面预览 1' },
    { src: '/demo/ui-demo2.png', alt: 'ModLink Studio 主界面预览 2' },
    { src: '/demo/ui-demo3.png', alt: 'ModLink Studio 主界面预览 3' },
]

const currentIndex = ref(0)

function showSlide(index: number): void {
    const total = slides.length
    currentIndex.value = ((index % total) + total) % total
}

function showPrevious(): void {
    showSlide(currentIndex.value - 1)
}

function showNext(): void {
    showSlide(currentIndex.value + 1)
}

function relativeIndex(index: number): number {
    return ((index - currentIndex.value) % slides.length + slides.length) % slides.length
}
</script>

<template>
    <div class="hero-demo-stack" aria-label="ModLink Studio 界面预览">
        <div class="hero-demo-stack__cards">
            <button
                v-for="(slide, index) in slides"
                :key="slide.src"
                type="button"
                class="hero-demo-stack__card"
                :class="{
                    'is-active': relativeIndex(index) === 0,
                    'is-middle': relativeIndex(index) === 1,
                    'is-back': relativeIndex(index) === 2,
                }"
                :aria-label="`查看第 ${index + 1} 张界面图`"
                @click="showSlide(index)"
            >
                <img :src="slide.src" :alt="slide.alt">
            </button>
        </div>

        <div class="hero-demo-stack__controls">
            <button
                type="button"
                class="hero-demo-stack__nav"
                aria-label="查看上一张界面图"
                @click="showPrevious"
            >
                ‹
            </button>

            <div class="hero-demo-stack__dots" role="tablist" aria-label="界面图分页">
                <button
                    v-for="(slide, index) in slides"
                    :key="`${slide.src}-dot`"
                    type="button"
                    class="hero-demo-stack__dot"
                    :class="{ 'is-active': index === currentIndex }"
                    :aria-label="`切换到第 ${index + 1} 张界面图`"
                    :aria-selected="index === currentIndex"
                    @click="showSlide(index)"
                />
            </div>

            <button
                type="button"
                class="hero-demo-stack__nav"
                aria-label="查看下一张界面图"
                @click="showNext"
            >
                ›
            </button>
        </div>
    </div>
</template>

<style scoped>
.hero-demo-stack {
    width: min(100%, 480px);
    margin: 0 auto;
}

.hero-demo-stack__cards {
    position: relative;
    min-height: 330px;
    padding: 0.85rem 1.5rem 1.45rem 0.85rem;
    isolation: isolate;
}

.hero-demo-stack__cards::before {
    content: '';
    position: absolute;
    inset: 4% 4% 9% 5%;
    z-index: 0;
    border-radius: 32px;
    background:
        radial-gradient(circle at 18% 24%, rgba(66, 99, 235, 0.24), transparent 34%),
        radial-gradient(circle at 80% 24%, rgba(14, 165, 233, 0.18), transparent 30%),
        radial-gradient(circle at 50% 82%, rgba(99, 102, 241, 0.14), transparent 28%),
        linear-gradient(135deg, rgba(255, 255, 255, 0.56), rgba(231, 238, 249, 0.12));
    filter: blur(26px);
    opacity: 0.92;
    pointer-events: none;
}

.hero-demo-stack__card {
    position: absolute;
    inset: 0;
    margin: 0;
    padding: 0;
    border: 0;
    border-radius: 22px;
    overflow: hidden;
    background:
        radial-gradient(circle at top left, rgba(42, 109, 244, 0.16), transparent 38%),
        radial-gradient(circle at bottom right, rgba(15, 23, 42, 0.1), transparent 36%),
        linear-gradient(180deg, rgba(247, 250, 255, 0.98), rgba(233, 239, 248, 0.96));
    cursor: pointer;
    transition:
        transform 0.38s ease,
        opacity 0.38s ease,
        filter 0.38s ease,
        background 0.38s ease;
}

.hero-demo-stack__card img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center 0%;
    transform: scale(1.07);
    transform-origin: center center;
    -webkit-mask-image: radial-gradient(
        ellipse at center,
        rgba(0, 0, 0, 1) 60%,
        rgba(0, 0, 0, 0.96) 72%,
        rgba(0, 0, 0, 0.72) 82%,
        rgba(0, 0, 0, 0.28) 90%,
        rgba(0, 0, 0, 0) 97%
    );
    mask-image: radial-gradient(
        ellipse at center,
        rgba(0, 0, 0, 1) 60%,
        rgba(0, 0, 0, 0.96) 72%,
        rgba(0, 0, 0, 0.72) 82%,
        rgba(0, 0, 0, 0.28) 90%,
        rgba(0, 0, 0, 0) 97%
    );
}

.hero-demo-stack__card.is-active {
    z-index: 3;
    opacity: 1;
    filter: saturate(1);
    transform: translate3d(0, 0, 0) rotate(-1deg) scale(1);
    background:
        radial-gradient(circle at top left, rgba(42, 109, 244, 0.15), transparent 38%),
        radial-gradient(circle at bottom right, rgba(14, 165, 233, 0.08), transparent 34%),
        linear-gradient(180deg, rgba(248, 251, 255, 0.99), rgba(236, 242, 250, 0.97));
}

.hero-demo-stack__card.is-middle {
    z-index: 2;
    opacity: 0.9;
    filter: saturate(0.95);
    transform: translate3d(16px, 14px, 0) rotate(4deg) scale(0.95);
}

.hero-demo-stack__card.is-back {
    z-index: 1;
    opacity: 0.72;
    filter: saturate(0.84);
    transform: translate3d(30px, 24px, 0) rotate(7deg) scale(0.91);
}

.hero-demo-stack__controls {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.85rem;
    margin-top: 0.2rem;
}

.hero-demo-stack__nav {
    width: 2.5rem;
    height: 2.5rem;
    border: 1px solid rgba(148, 163, 184, 0.28);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.9);
    color: var(--vp-c-text-1);
    font-size: 1.4rem;
    line-height: 1;
    cursor: pointer;
    transition: transform 0.2s ease, background-color 0.2s ease;
}

.hero-demo-stack__nav:hover {
    background: rgba(42, 109, 244, 0.12);
}

.hero-demo-stack__nav:active {
    transform: scale(0.97);
}

.hero-demo-stack__dots {
    display: flex;
    align-items: center;
    gap: 0.55rem;
}

.hero-demo-stack__dot {
    width: 0.72rem;
    height: 0.72rem;
    border: 0;
    border-radius: 999px;
    background: rgba(100, 116, 139, 0.3);
    cursor: pointer;
    transition: transform 0.2s ease, background-color 0.2s ease;
}

.hero-demo-stack__dot.is-active {
    background: var(--vp-c-brand-1);
    transform: scale(1.15);
}

@media (max-width: 959px) {
    .hero-demo-stack {
        width: min(100%, 375px);
    }

    .hero-demo-stack__cards {
        min-height: 290px;
        padding: 0.7rem 1.12rem 1rem 0.7rem;
    }

    .hero-demo-stack__card.is-middle {
        transform: translate3d(11px, 10px, 0) rotate(4deg) scale(0.95);
    }

    .hero-demo-stack__card.is-back {
        transform: translate3d(21px, 18px, 0) rotate(7deg) scale(0.91);
    }
}
</style>
