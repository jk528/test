<script setup lang="ts">
import { computed, ref } from "vue";
import type { Chapter } from "../lib/chapters";

const props = defineProps<{
  chapters: Chapter[];
  activeIndex: number; // 1 基，0=无
}>();

const emit = defineEmits<{
  (e: "select", index1: number): void;
}>();

const keyword = ref("");

const filtered = computed(() => {
  const kw = keyword.value.trim();
  if (!kw) return props.chapters;
  return props.chapters.filter(
    (c) => c.title.includes(kw) || c.numberText.includes(kw)
  );
});

function pad(n: number): string {
  return n.toString().padStart(3, " ");
}
</script>

<template>
  <div class="chapter-tree">
    <div class="tree-search">
      <input
        v-model="keyword"
        type="text"
        placeholder="搜索回目…"
        spellcheck="false"
      />
    </div>
    <div class="tree-list">
      <button
        v-for="ch in filtered"
        :key="ch.index"
        class="tree-item"
        :class="{ active: ch.index === activeIndex }"
        @click="emit('select', ch.index)"
      >
        <span class="tree-no">{{ pad(ch.index) }}</span>
        <span class="tree-title">{{ ch.name || ch.title }}</span>
      </button>
      <div v-if="filtered.length === 0" class="tree-empty">无匹配回目</div>
    </div>
  </div>
</template>

<style scoped>
.chapter-tree {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.tree-search {
  padding: 8px 10px;
  border-bottom: 1px solid #e6ddc7;
}
.tree-search input {
  width: 100%;
  box-sizing: border-box;
  padding: 6px 10px;
  border: 1px solid #d8ccad;
  border-radius: 6px;
  font-size: 13px;
  background: #fffdf7;
  color: #2b2620;
}
.tree-search input:focus {
  outline: none;
  border-color: #c9a35c;
}
.tree-list {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding: 6px;
}
.tree-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  width: 100%;
  text-align: left;
  padding: 6px 8px;
  margin-bottom: 2px;
  border: none;
  border-radius: 6px;
  background: transparent;
  cursor: pointer;
  color: #3a332a;
  font-size: 13px;
  line-height: 1.35;
}
.tree-item:hover {
  background: #f3ead3;
}
.tree-item.active {
  background: #ead9b4;
  color: #6b4e16;
  font-weight: 600;
}
.tree-no {
  flex: 0 0 auto;
  font-variant-numeric: tabular-nums;
  color: #a08b5e;
  font-size: 12px;
  min-width: 26px;
}
.tree-title {
  flex: 1;
}
.tree-empty {
  padding: 20px;
  text-align: center;
  color: #a08b5e;
  font-size: 13px;
}
</style>
