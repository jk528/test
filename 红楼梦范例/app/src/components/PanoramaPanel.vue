<script setup lang="ts">
// M4 全景分析面板：事件时间线 / 人物榜与角色卡 / 伏笔起收。
// 数据来自 sidecar 的 M4 方法（既有 120 章 V3.4 报告回灌进 SQLite）。
// 每条都带物理行锚点，点击 emit jump → App 侧 revealLine 跳回正文。
import { computed, onMounted, ref, watch } from "vue";
import {
  overview,
  listEvents,
  listEntities,
  getEntity,
  listForeshadows,
  type Overview,
  type BookEvent,
  type EntityRow,
  type Foreshadow,
  type EntityRelation,
} from "../lib/sidecar";
import type { Chapter } from "../lib/chapters";

const props = defineProps<{
  bookId: string;
  chapters: Chapter[];
  /** 外部（如 AI 面板）选中的实体，用于同步高亮态 */
  activeEntity?: string | null;
}>();

const emit = defineEmits<{
  (e: "jump", line0: number): void;
  (e: "pick-entity", canonical: string | null): void;
}>();

type Tab = "events" | "entities" | "foreshadows";
const tab = ref<Tab>("events");
const busy = ref(false);
const err = ref("");

const ov = ref<Overview | null>(null);
const events = ref<BookEvent[]>([]);
const entities = ref<EntityRow[]>([]);
const foreshadows = ref<Foreshadow[]>([]);

// 事件筛选
const levelFilter = ref<"" | "主线" | "支线" | "细节">("");
const entityFilter = ref<string>("");

// 角色卡
const card = ref<{
  entity: EntityRow;
  curve: { chapter_idx: number; n: number }[];
  relations: EntityRelation[];
} | null>(null);
const picked = ref<string | null>(null);

const filteredEvents = computed(() =>
  events.value.filter(
    (e) =>
      (!levelFilter.value || e.level === levelFilter.value) &&
      (!entityFilter.value || e.participants.includes(entityFilter.value))
  )
);

/** 事件按章分组（章号 1-based） */
const eventsByChapter = computed(() => {
  const map = new Map<number, BookEvent[]>();
  for (const e of filteredEvents.value) {
    const k = e.chapter_idx + 1;
    const arr = map.get(k);
    if (arr) arr.push(e);
    else map.set(k, [e]);
  }
  return [...map.entries()].sort((a, b) => a[0] - b[0]);
});

function chapterLabel(idx0: number): string {
  const ch = props.chapters[idx0];
  if (!ch) return `第${idx0 + 1}回`;
  return `第${ch.numberText}${ch.unit}`;
}

async function loadAll() {
  if (!props.bookId) return;
  busy.value = true;
  err.value = "";
  try {
    ov.value = await overview(props.bookId);
    const [ev, ent, fs] = await Promise.all([
      listEvents({ book_id: props.bookId, limit: 3000 }),
      listEntities(props.bookId, 1, 60),
      listForeshadows(props.bookId),
    ]);
    events.value = ev.events;
    entities.value = ent.entities;
    foreshadows.value = fs.foreshadows;
  } catch (e) {
    err.value = String(e);
  } finally {
    busy.value = false;
  }
}

async function pickEntity(name: string) {
  if (picked.value === name) {
    picked.value = null;
    card.value = null;
    emit("pick-entity", null);
    return;
  }
  picked.value = name;
  emit("pick-entity", name);
  try {
    card.value = await getEntity(props.bookId, name);
  } catch (e) {
    err.value = String(e);
  }
}

/** 出场曲线 → 归一化柱高（按最大章出场数） */
const curveBars = computed(() => {
  if (!card.value) return [];
  const max = Math.max(1, ...card.value.curve.map((c) => c.n));
  return card.value.curve.map((c) => ({
    ch: c.chapter_idx + 1,
    n: c.n,
    h: Math.max(4, Math.round((c.n / max) * 100)),
  }));
});

/** 锚点精度徽标：让「近似锚点」在界面上可见，不假装精确 */
function precBadge(p: string): string {
  return p === "quote" ? "精确" : p === "cooccur" ? "近似" : "粗定位";
}

onMounted(loadAll);
watch(() => props.bookId, loadAll);
watch(
  () => props.activeEntity,
  (v) => {
    if (v === undefined) return;
    if (v !== picked.value) picked.value = v;
  }
);
</script>

<template>
  <div class="pano">
    <div class="pano-summary" v-if="ov">
      <span class="ps-item"><b>{{ ov.events }}</b> 事件</span>
      <span class="ps-item"><b>{{ ov.entities }}</b> 人物</span>
      <span class="ps-item"><b>{{ ov.foreshadows }}</b> 伏笔</span>
      <span class="ps-item"><b>{{ ov.relations }}</b> 关系</span>
      <span class="ps-item dim">{{ ov.chapters_with_events }}/120 回</span>
    </div>

    <div class="pano-tabs">
      <button :class="{ on: tab === 'events' }" @click="tab = 'events'">
        事件 {{ ov?.events ?? "" }}
      </button>
      <button :class="{ on: tab === 'entities' }" @click="tab = 'entities'">
        人物 {{ ov?.entities ?? "" }}
      </button>
      <button :class="{ on: tab === 'foreshadows' }" @click="tab = 'foreshadows'">
        伏笔 {{ ov?.foreshadows ?? "" }}
      </button>
    </div>

    <div v-if="err" class="pano-err">{{ err }}</div>
    <div v-else-if="busy" class="pano-hint">加载全景数据…</div>

    <!-- ── 事件时间线 ── -->
    <div v-show="tab === 'events'" class="pano-body">
      <div class="filters">
        <select v-model="levelFilter">
          <option value="">全部级别</option>
          <option value="主线">主线</option>
          <option value="支线">支线</option>
          <option value="细节">细节</option>
        </select>
        <select v-model="entityFilter">
          <option value="">全部人物</option>
          <option v-for="e in entities.slice(0, 40)" :key="e.id" :value="e.canonical">
            {{ e.canonical }} ({{ e.appear_count }})
          </option>
        </select>
        <span class="cnt">{{ filteredEvents.length }} 条</span>
      </div>
      <div class="scroll">
        <div v-for="[ch, list] in eventsByChapter" :key="ch" class="ch-group">
          <div class="ch-head">{{ chapterLabel(ch - 1) }} · {{ list.length }} 事件</div>
          <div
            v-for="e in list"
            :key="e.id"
            class="ev-item"
            :class="'lv-' + e.level"
            @click="emit('jump', e.line_start)"
          >
            <span class="ev-uid">{{ e.event_uid }}</span>
            <span class="ev-lv">{{ e.level }}</span>
            <span class="ev-sum">{{ e.summary }}</span>
            <span class="ev-prec" :title="'锚点精度：' + e.anchor_precision">
              {{ precBadge(e.anchor_precision) }}
            </span>
            <span class="ev-line">L{{ e.line_start }}</span>
          </div>
        </div>
        <div v-if="eventsByChapter.length === 0" class="pano-hint">无匹配事件</div>
      </div>
    </div>

    <!-- ── 人物榜 + 角色卡 ── -->
    <div v-show="tab === 'entities'" class="pano-body">
      <div class="scroll">
        <div class="ent-list">
          <div
            v-for="e in entities"
            :key="e.id"
            class="ent-item"
            :class="{ on: picked === e.canonical }"
            @click="pickEntity(e.canonical)"
          >
            <span class="ent-name">{{ e.canonical }}</span>
            <span class="ent-bar"><i :style="{ width: Math.min(100, e.appear_count / 45) + '%' }"></i></span>
            <span class="ent-n">{{ e.appear_count }}</span>
          </div>
        </div>

        <div v-if="card" class="card">
          <div class="card-head">
            <b>{{ card.entity.canonical }}</b>
            <span class="dim">出场 {{ card.entity.appear_count }} 次 · 首见{{ chapterLabel((card.entity.first_chapter ?? 0)) }}</span>
            <button class="mini" @click="pickEntity(card.entity.canonical)">关闭</button>
          </div>
          <div v-if="card.entity.aliases.length" class="card-alias">
            别名：{{ card.entity.aliases.join("、") }}
          </div>
          <div class="card-sec">
            <div class="sec-title">逐回出场（点击柱跳转）</div>
            <div class="curve">
              <i
                v-for="b in curveBars"
                :key="b.ch"
                :style="{ height: b.h + '%' }"
                :title="`第${b.ch}回 ${b.n} 次`"
                @click="emit('jump', (chapters[b.ch - 1]?.line ?? 0))"
              ></i>
            </div>
          </div>
          <div class="card-sec">
            <div class="sec-title">关系（{{ card.relations.length }}）</div>
            <div
              v-for="r in card.relations.slice(0, 12)"
              :key="r.id"
              class="rel"
              @click="emit('jump', 0)"
            >
              <span class="rel-a">{{ r.entity_a }}</span>
              <span class="rel-mid">{{ r.relation }}</span>
              <span class="rel-b">{{ r.entity_b }}</span>
              <span class="rel-ch">{{ chapterLabel(r.chapter_idx) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── 伏笔起收 ── -->
    <div v-show="tab === 'foreshadows'" class="pano-body">
      <div class="scroll">
        <div
          v-for="f in foreshadows"
          :key="f.id"
          class="fs-item"
          @click="emit('jump', f.setup_line)"
        >
          <span class="fs-ch">{{ chapterLabel(f.setup_chapter) }}</span>
          <span class="fs-kind">{{ f.kind }}</span>
          <span class="fs-content">{{ f.content }}</span>
          <span class="fs-st" :class="f.status">
            {{ f.status === "closed" ? "已呼应" : "未呼应" }}
          </span>
          <span v-if="f.payoff_chapter !== null" class="fs-pay">
            → {{ chapterLabel(f.payoff_chapter) }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pano {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
  font-size: 12px;
  color: #333;
}
.pano-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 6px 10px;
  background: #faf7f0;
  border-bottom: 1px solid #e6ded0;
  flex-shrink: 0;
}
.ps-item b {
  color: #7a5410;
}
.ps-item.dim,
.dim {
  color: #999;
}
.pano-tabs {
  display: flex;
  border-bottom: 1px solid #e0e0e0;
  flex-shrink: 0;
}
.pano-tabs button {
  flex: 1;
  border: none;
  background: #fff;
  padding: 6px 0;
  cursor: pointer;
  font-size: 12px;
  color: #666;
  border-bottom: 2px solid transparent;
}
.pano-tabs button.on {
  color: #7a5410;
  border-bottom-color: #c9a35c;
  font-weight: 700;
}
.pano-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.filters {
  display: flex;
  gap: 6px;
  align-items: center;
  padding: 5px 8px;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}
.filters select {
  font-size: 12px;
  max-width: 120px;
  border: 1px solid #ddd;
  border-radius: 3px;
  padding: 2px 4px;
  background: #fff;
}
.filters .cnt {
  margin-left: auto;
  color: #999;
}
.scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 4px 6px 20px;
}
.pano-hint {
  padding: 10px;
  color: #999;
}
.pano-err {
  padding: 8px;
  color: #c62828;
  background: #ffebee;
}
.ch-group {
  margin-bottom: 6px;
}
.ch-head {
  position: sticky;
  top: 0;
  background: #f6ead0;
  color: #7a5410;
  font-weight: 700;
  padding: 3px 6px;
  border-radius: 3px;
  z-index: 1;
}
.ev-item {
  display: flex;
  align-items: baseline;
  gap: 5px;
  padding: 3px 6px;
  cursor: pointer;
  border-left: 3px solid #ddd;
  border-radius: 2px;
  line-height: 1.5;
}
.ev-item:hover {
  background: #fdf6e8;
}
.ev-item.lv-主线 {
  border-left-color: #c62828;
}
.ev-item.lv-支线 {
  border-left-color: #1565c0;
}
.ev-item.lv-细节 {
  border-left-color: #9e9e9e;
}
.ev-uid {
  color: #999;
  font-family: Consolas, monospace;
  flex-shrink: 0;
}
.ev-lv {
  color: #7a5410;
  flex-shrink: 0;
}
.ev-sum {
  flex: 1;
  min-width: 0;
}
.ev-prec {
  color: #8d6e63;
  background: #f5f0e6;
  border-radius: 2px;
  padding: 0 3px;
  flex-shrink: 0;
}
.ev-line {
  color: #bbb;
  font-family: Consolas, monospace;
  flex-shrink: 0;
}
.ent-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.ent-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 6px;
  cursor: pointer;
  border-radius: 3px;
}
.ent-item:hover {
  background: #f5f5f5;
}
.ent-item.on {
  background: #fdf6e8;
  outline: 1px solid #e0c98a;
}
.ent-name {
  width: 68px;
  flex-shrink: 0;
  font-weight: 700;
}
.ent-bar {
  flex: 1;
  height: 8px;
  background: #eee;
  border-radius: 4px;
  overflow: hidden;
}
.ent-bar i {
  display: block;
  height: 100%;
  background: #c9a35c;
}
.ent-n {
  width: 42px;
  text-align: right;
  color: #888;
  font-family: Consolas, monospace;
}
.card {
  margin: 8px 2px;
  padding: 8px;
  border: 1px solid #e6ded0;
  border-radius: 4px;
  background: #fffdf8;
}
.card-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.card-head .mini {
  margin-left: auto;
  border: 1px solid #ddd;
  background: #fff;
  border-radius: 3px;
  font-size: 11px;
  cursor: pointer;
}
.card-alias {
  color: #8d6e63;
  margin-top: 2px;
}
.card-sec {
  margin-top: 8px;
}
.sec-title {
  color: #7a5410;
  font-weight: 700;
  margin-bottom: 3px;
}
.curve {
  display: flex;
  align-items: flex-end;
  gap: 1px;
  height: 54px;
  padding: 2px;
  background: #fff;
  border: 1px solid #eee;
  border-radius: 3px;
}
.curve i {
  flex: 1;
  min-width: 2px;
  background: #b98a3c;
  cursor: pointer;
  border-radius: 1px 1px 0 0;
}
.curve i:hover {
  background: #c62828;
}
.rel {
  display: flex;
  gap: 6px;
  padding: 2px 4px;
  cursor: default;
  border-bottom: 1px dashed #f0f0f0;
}
.rel-mid {
  color: #1565c0;
}
.rel-ch {
  margin-left: auto;
  color: #aaa;
}
.fs-item {
  display: flex;
  align-items: baseline;
  gap: 5px;
  padding: 3px 6px;
  cursor: pointer;
  border-left: 3px solid #b0bec5;
  border-radius: 2px;
  line-height: 1.5;
}
.fs-item:hover {
  background: #fdf6e8;
}
.fs-ch {
  color: #7a5410;
  flex-shrink: 0;
}
.fs-kind {
  color: #8d6e63;
  flex-shrink: 0;
}
.fs-content {
  flex: 1;
  min-width: 0;
}
.fs-st {
  flex-shrink: 0;
  border-radius: 2px;
  padding: 0 3px;
}
.fs-st.open {
  background: #fff3e0;
  color: #e65100;
}
.fs-st.closed {
  background: #e8f5e9;
  color: #2e7d32;
}
.fs-pay {
  color: #1565c0;
  flex-shrink: 0;
}
</style>
