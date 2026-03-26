import { defineConfig } from 'vitepress'

export default defineConfig({
    lang: 'zh-CN',
    title: 'ModLink Studio',
    description: '面向设备接入、多模态采集与展示的平台文档',
    head: [
        ['link', { rel: 'icon', href: '/favicon.ico' }],
    ],
    base: '/',
    cleanUrls: true,
    lastUpdated: true,
    themeConfig: {
        siteTitle: 'ModLink Studio',
        outline: {
            label: '本页目录',
            level: [2, 3],
        },
        nav: [
            { text: '首页', link: '/' },
            { text: '安装', link: '/install' },
            { text: 'SDK', link: '/sdk' },
            { text: 'Core', link: '/core' },
            { text: 'UI', link: '/ui' },
            { text: 'App', link: '/app' },
            { text: 'API', link: '/api' },
        ],
        sidebar: {
            '/': [
                {
                    text: '快速开始',
                    items: [
                        { text: '首页', link: '/' },
                        { text: '安装与发布', link: '/install' },
                        { text: 'SDK 开发者指南', link: '/sdk' },
                        { text: 'Core 模块架构', link: '/core' },
                        { text: 'UI 模块架构', link: '/ui' },
                        { text: 'App 组合根', link: '/app' },
                        { text: 'API 快速索引', link: '/api' },
                    ],
                },
            ],
        },
        footer: {
            message: 'Packages for ModLink Studio are hosted on Cloudsmith OSS.',
            copyright: 'Copyright © 2026',
        },
        socialLinks: [
            { icon: 'github', link: 'https://github.com/modlink-studio/ModLink-Studio' },
        ],
        search: {
            provider: 'local',
        },
    },
})

