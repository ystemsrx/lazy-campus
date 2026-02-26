import { computed } from 'vue';
const props = defineProps();
const prettyArguments = computed(() => {
    const raw = props.toolArguments?.trim();
    if (!raw)
        return '';
    try {
        return JSON.stringify(JSON.parse(raw), null, 2);
    }
    catch {
        return raw;
    }
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['agent-tool-card__head']} */ ;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "agent-tool-card" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "agent-tool-card__head" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.i, __VLS_intrinsicElements.i)({
    ...{ class: "fa-solid fa-screwdriver-wrench" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
(__VLS_ctx.toolName || 'Tool');
if (__VLS_ctx.toolCallId) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.code, __VLS_intrinsicElements.code)({});
    (__VLS_ctx.toolCallId);
}
if (__VLS_ctx.prettyArguments) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.pre, __VLS_intrinsicElements.pre)({
        ...{ class: "agent-tool-card__args" },
    });
    (__VLS_ctx.prettyArguments);
}
else {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "agent-tool-card__empty" },
    });
}
/** @type {__VLS_StyleScopedClasses['agent-tool-card']} */ ;
/** @type {__VLS_StyleScopedClasses['agent-tool-card__head']} */ ;
/** @type {__VLS_StyleScopedClasses['fa-solid']} */ ;
/** @type {__VLS_StyleScopedClasses['fa-screwdriver-wrench']} */ ;
/** @type {__VLS_StyleScopedClasses['agent-tool-card__args']} */ ;
/** @type {__VLS_StyleScopedClasses['agent-tool-card__empty']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            prettyArguments: prettyArguments,
        };
    },
    __typeProps: {},
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    __typeProps: {},
});
; /* PartiallyEnd: #4569/main.vue */
