<script setup lang="ts">
// M3：AI 问答面板 —— RAG 检索 + LLM 作答，答案引用带来源锚点。
import { ref } from "vue";
import { askAi, dbStatus, type DbStatus } from "../lib/sidecar";

const props = defineProps<{
  bookId: string;
  chapters: { index: number; name: string; line: number }[];
}>();

const emit = defineEmits<{
  // 点击来源锚点 → 跳到对应章节行
  (e: "jump", line0: number): void;
}>();

const input = ref("");
const asking = ref(false);
const answer = ref("");
const sources = ref<
  { id: number; chapter_idx: number; line_start: number; line_end: number }[]
>([]);
const errorMsg = ref("");
const status = ref<DbStatus | null>(null);

/** 章节索引 → 回目标题（用于来源标注） */
function chapterLabel(idx: number): string {
  const ch = props.chapters[idx];
  return ch ? `${idx + 1}. ${ch.name || ""}` : `第${idx + 1}章`;
}

/** 来源锚点 → 跳到该行（Monaco 滚动 + 高亮） */
function jumpTo(s: { line_start: number }) {
  emit("jump", s.line_start);
}

async function send() {
  const q = input.value.trim();
  if (!q || asking.value) return;
  asking.value = true;
  errorMsg.value = "";
  try {
    const r = await askAi({ query: q, book_id: props.bookId, use_rag: true });
    answer.value = r.answer;
    sources.value = r.sources;
    // 回答中的 [1][2] 引用编号与 sources 对应
  } catch (e) {
    errorMsg.value = String(e);
  } finally {
    asking.value = false;
  }
}

function fillQuestion(text: string) {
  if (text.trim()) input.value = text.trim().slice(0, 200);
}

defineExpose({ pickQuestion: fillQuestion });

async function refreshStatus() {
  try {
    status.value = await dbStatus();
  } catch {
    status.value = null;
  }
}
refreshStatus();
</script>

<template>
  <div class="ai-panel">
    <div class="ai-header">
      <span class="ai-title">AI 问答</span>
      <span v-if="status" class="ai-status" :class="{ bad: !status.vec_ready }">
        {{ status.vec_ready ? "向量库就绪" : "向量库未就绪" }}
      </span>
      <span v-if="status" class="ai-status" :class="{ bad: !status.llm_configured }">
        {{ status.llm_configured ? "LLM 已配置" : "LLM 未配置" }}
      </span>
    </div>

    <div class="ai-body">
      <div v-if="errorMsg" class="ai-error">{{ errorMsg }}</div>
      <div v-if="answer" class="ai-answer">
        <div class="ai-answer-text">{{ answer }}</div>
        <div v-if="sources.length" class="ai-sources">
          <div class="ai-sources-title">来源（点击跳转）：</div>
          <button
            v-for="s in sources"
            :key="s.id"
            class="ai-source"
            @click="jumpTo(s)"
          >
            {{ chapterLabel(s.chapter_idx) }} · 行{{ s.line_start + 1 }}
          </button>
        </div>
      </div>
      <div v-else-if="!asking" class="ai-hint">
        在正文选中文字可自动填入提问；或直接输入问题，
        <br />如「林黛玉初进贾府时的心理状态」。
      </div>
      <div v-if="asking" class="ai-asking">思考中…</div>
    </div>

    <div class="ai-input-bar">
      <textarea
        v-model="input"
        rows="2"
        placeholder="提问《红楼梦》…"
        @keydown.enter.exact.prevent="send()"
      />
      <button class="ai-send" :disabled="asking || !input.trim()" @click="send()">
        发送
      </button>
    </div>
  </div>
</template>

<style scoped>
.ai-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: #fffdf7;
  border-left: 1px solid #e6ddc7;
}
.ai-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid #e6ddc7;
  background: #faf5e8;
  font-size: 13px;
}
.ai-title {
  font-weight: 700;
  color: #6b4e16;
}
.ai-status {
  font-size: 11px;
  color: #2e7d32;
  padding: 1px 6px;
  border-radius: 4px;
  background: #e8f5e9;
}
.ai-status.bad {
  color: #c0392b;
  background: #fdecea;
}
.ai-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.7;
}
.ai-error {
  color: #c0392b;
  background: #fdecea;
  padding: 8px;
  border-radius: 6px;
  margin-bottom: 8px;
}
.ai-answer-text {
  white-space: pre-wrap;
  color: #2b2620;
}
.ai-sources {
  margin-top: 12px;
  border-top: 1px dashed #d8ccad;
  padding-top: 8px;
}
.ai-sources-title {
  font-size: 12px;
  color: #8a6d3b;
  margin-bottom: 6px;
}
.ai-source {
  display: inline-block;
  margin: 0 6px 6px 0;
  padding: 4px 10px;
  border: 1px solid #d8ccad;
  border-radius: 12px;
  background: #faf5e8;
  color: #6b4e16;
  font-size: 12px;
  cursor: pointer;
}
.ai-source:hover {
  background: #ead9b4;
}
.ai-asking {
  color: #a08b5e;
  font-size: 12px;
  margin-top: 8px;
}
.ai-input-bar {
  display: flex;
  gap: 6px;
  padding: 8px 10px;
  border-top: 1px solid #e6ddc7;
}
.ai-input-bar textarea {
  flex: 1;
  resize: none;
  border: 1px solid #d8ccad;
  border-radius: 8px;
  padding: 6px 8px;
  font-size: 13px;
  background: #fff;
  color: #2b2620;
  outline: none;
}
.ai-input-bar textarea:focus {
  border-color: #c9a35c;
}
.ai-send {
  align-self: flex-end;
  border: none;
  background: #c9a35c;
  color: #3a2a08;
  font-weight: 600;
  font-size: 13px;
  padding: 8px 14px;
  border-radius: 8px;
  cursor: pointer;
}
.ai-send:disabled {
  opacity: 0.5;
  cursor: default;
}
</style>