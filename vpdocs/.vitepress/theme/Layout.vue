<script setup lang="ts">
import DefaultTheme from 'vitepress/theme'

import HeroDemoStack from './components/HeroDemoStack.vue'
</script>

<template>
    <DefaultTheme.Layout>
        <template #home-hero-image>
            <HeroDemoStack />
        </template>
    </DefaultTheme.Layout>
</template>
