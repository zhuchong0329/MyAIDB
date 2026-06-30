// TypeScript source for the ZeroAgentMemory browser UI.
// The Python renderer embeds the compiled JavaScript snapshot next to this file.

type GraphMode = "init" | "drilldown" | "focus" | "all";
type MetricKey =
  | "recall_count"
  | "selected_count"
  | "helpful_count"
  | "missed_recall_count"
  | "hotness_score"
  | "stale_hit_count"
  | "false_positive_count";

interface MemoryRoute {
  route: string;
  count: number;
}

interface MemoryMetrics {
  recall_count: number;
  selected_count: number;
  helpful_count: number;
  used_in_final_answer_count: number;
  stale_hit_count: number;
  false_positive_count: number;
  missed_recall_count: number;
  hotness_score: number;
  common_routes: MemoryRoute[];
  last_used_at: string;
  [key: string]: unknown;
}

interface MemoryNode {
  id: string;
  name: string;
  description: string;
  layer: string;
  status: string;
  pattern_key: string;
  component: string;
  kind: string;
  parents: string[];
  load_next: string[];
  related: string[];
  related_files: string[];
  related_symbols: string[];
  tags: string[];
  path: string;
  freshness_profile: string;
  freshness_source: string;
  metrics: MemoryMetrics;
  graph_score: number;
}

interface MemoryEdge {
  source: string;
  target: string;
  type: string;
}

interface DashboardData {
  metadata: {
    memory_count: number;
    edge_count: number;
    event_count: number;
    window_days: number;
    writer_scope: string;
    max_graph_nodes: number;
    generated_at: string;
    root: string;
    workspace_root?: string;
    file_link_base?: string;
    file_links?: Record<string, string>;
    file_raw_links?: Record<string, string>;
    source_min_timestamp?: string;
    source_max_timestamp?: string;
    [key: string]: unknown;
  };
  nodes: MemoryNode[];
  edges: MemoryEdge[];
}

interface AppState {
  query: string;
  layer: string;
  status: string;
  sortKey: string;
  graphMode: GraphMode;
  nodeLimit: number;
  selectedId: string | null;
}

interface Element {
  setAttribute(qualifiedName: string, value: string | number): void;
}

const DATA: DashboardData = JSON.parse(document.getElementById('memory-data').textContent);
    const state: AppState = {
      query: '',
      layer: 'all',
      status: 'all',
      sortKey: 'hotness_score',
      graphMode: 'init',
      nodeLimit: DATA.metadata.max_graph_nodes,
      selectedId: null,
    };
    const byId = new Map<string, MemoryNode>(DATA.nodes.map(node => [node.id, node]));
    const numberKeys = new Set<string>([
      'recall_count',
      'selected_count',
      'helpful_count',
      'missed_recall_count',
      'hotness_score',
    ]);

    function metric(node, key) {
      return node.metrics[key] ?? 0;
    }

    function pad2(value: number): string {
      return String(value).padStart(2, '0');
    }

    function timezoneOffset(date: Date): string {
      const offsetMinutes = -date.getTimezoneOffset();
      const sign = offsetMinutes >= 0 ? '+' : '-';
      const absolute = Math.abs(offsetMinutes);
      return `${sign}${pad2(Math.floor(absolute / 60))}:${pad2(absolute % 60)}`;
    }

    function formatTimestamp(value?: string): string {
      if (!value) return 'none';
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      return [
        date.getFullYear(),
        '-',
        pad2(date.getMonth() + 1),
        '-',
        pad2(date.getDate()),
        'T',
        pad2(date.getHours()),
        ':',
        pad2(date.getMinutes()),
        ':',
        pad2(date.getSeconds()),
        timezoneOffset(date),
      ].join('');
    }

    function searchable(node) {
      return [
        node.id,
        node.name,
        node.description,
        node.layer,
        node.status,
        node.pattern_key,
        node.component,
        node.kind,
        ...(node.related_files || []),
        ...(node.related_symbols || []),
        ...(node.tags || []),
      ].join(' ').toLowerCase();
    }

    function filteredNodes() {
      const query = state.query.trim().toLowerCase();
      return DATA.nodes.filter(node => {
        if (state.layer !== 'all' && node.layer !== state.layer) return false;
        if (state.status !== 'all' && node.status !== state.status) return false;
        if (query && !searchable(node).includes(query)) return false;
        return true;
      });
    }

    function sortedNodes(nodes) {
      const key = state.sortKey;
      return [...nodes].sort((a, b) => {
        if (key === 'last_used_at') {
          return (b.metrics.last_used_at || '').localeCompare(a.metrics.last_used_at || '') || a.id.localeCompare(b.id);
        }
        if (numberKeys.has(key)) {
          return (metric(b, key) - metric(a, key)) || a.id.localeCompare(b.id);
        }
        return String(a[key] || '').localeCompare(String(b[key] || '')) || a.id.localeCompare(b.id);
      });
    }

    function uniqueNodes(nodes) {
      const seen = new Set();
      const result = [];
      for (const node of nodes) {
        if (seen.has(node.id)) continue;
        seen.add(node.id);
        result.push(node);
      }
      return result;
    }

    function selectedMemoryFor(nodes) {
      if (state.selectedId && nodes.some(node => node.id === state.selectedId)) {
        return byId.get(state.selectedId);
      }
      return sortedNodes(nodes)[0] || null;
    }

    function selectedRelationshipIds(selected) {
      if (!selected) return new Set();
      const ids = new Set([
        selected.id,
        ...(selected.parents || []),
        ...(selected.load_next || []),
        ...(selected.related || []),
      ]);
      for (const node of DATA.nodes) {
        if ((node.related || []).includes(selected.id)) ids.add(node.id);
        if ((node.load_next || []).includes(selected.id)) ids.add(node.id);
      }
      return ids;
    }

    function drilldownNodes(nodes) {
      const selected = selectedMemoryFor(nodes);
      if (!selected) return [];
      const limit = Math.max(12, Math.min(state.nodeLimit, nodes.length));
      const ids = selectedRelationshipIds(selected);
      const correlated = nodes.filter(node => ids.has(node.id));
      const selectedNode = correlated.filter(node => node.id === selected.id);
      const priority = { upstream: 0, load_next: 1, related: 2, correlated: 3, selected: 4 };
      const rest = correlated.filter(node => node.id !== selected.id)
        .sort((a, b) => {
          const groupA = relationshipGroup(a, selected);
          const groupB = relationshipGroup(b, selected);
          return (priority[groupA] - priority[groupB])
            || (graphScoreForLabel(b) - graphScoreForLabel(a))
            || a.id.localeCompare(b.id);
        })
        .slice(0, Math.max(0, limit - selectedNode.length));
      return uniqueNodes([...selectedNode, ...rest]);
    }

    function graphNodes(nodes) {
      if (state.graphMode === 'all') return sortedNodes(nodes);
      if (state.graphMode === 'init') {
        const initNodes = sortedNodes(nodes.filter(node => node.layer === 'init'));
        return initNodes.length ? initNodes : sortedNodes(nodes).slice(0, Math.min(state.nodeLimit, nodes.length));
      }
      if (state.graphMode === 'drilldown') return drilldownNodes(nodes);

      const limit = Math.max(12, Math.min(state.nodeLimit, nodes.length));
      const selected = state.selectedId
        ? nodes.filter(node => node.id === state.selectedId)
        : [];
      const initNodes = nodes.filter(node => node.layer === 'init');
      const required = uniqueNodes([...selected, ...initNodes]);
      const requiredIds = new Set(required.map(node => node.id));
      const filler = sortedNodes(nodes.filter(node => !requiredIds.has(node.id)))
        .slice(0, Math.max(0, limit - required.length));
      return uniqueNodes([...required, ...filler]).slice(0, limit);
    }

    function compactLabel(id) {
      if (id.length <= 34) return id;
      const parts = id.split('.');
      if (parts.length >= 3) {
        const compact = `${parts[0]}.${parts[1]}.${parts[parts.length - 1]}`;
        if (compact.length <= 34) return compact;
      }
      return `${id.slice(0, 31)}...`;
    }

    function compactDrilldownLabel(id) {
      if (id.length <= 28) return id;
      const parts = id.split('.');
      if (parts.length >= 3) {
        const compact = `${parts[0]}.${parts[parts.length - 2]}.${parts[parts.length - 1]}`;
        if (compact.length <= 28) return compact;
      }
      return `${id.slice(0, 25)}...`;
    }

    function shouldLabel(node, index, labelIds = null) {
      if (labelIds) return labelIds.has(node.id);
      if (node.id === state.selectedId) return true;
      if (node.layer === 'init') return true;
      if (state.graphMode === 'init') return true;
      if (state.graphMode === 'drilldown') return true;
      return index < 18 && graphScoreForLabel(node) > 0;
    }

    function graphScoreForLabel(node) {
      return metric(node, 'hotness_score')
        + metric(node, 'recall_count')
        + metric(node, 'helpful_count')
        + metric(node, 'missed_recall_count');
    }

    function graphEdges(nodeSet) {
      const visible = DATA.edges.filter(edge => nodeSet.has(edge.source) && nodeSet.has(edge.target));
      if (state.graphMode === 'all') return visible;
      if (state.graphMode === 'init') return [];
      const selectedEdges = state.selectedId
        ? visible.filter(edge => edge.source === state.selectedId || edge.target === state.selectedId)
        : [];
      if (state.graphMode === 'drilldown' && state.selectedId) return selectedEdges;
      const selectedKeys = new Set(selectedEdges.map(edge => `${edge.source}|${edge.target}|${edge.type}`));
      const edgeLimit = state.graphMode === 'drilldown' ? 80 : 80;
      const rest = visible
        .filter(edge => !selectedKeys.has(`${edge.source}|${edge.target}|${edge.type}`))
        .sort((a, b) => (a.type === 'load_next' ? 0 : 1) - (b.type === 'load_next' ? 0 : 1));
      return [...selectedEdges, ...rest].slice(0, edgeLimit);
    }

    function nodeColor(node) {
      if (metric(node, 'missed_recall_count') > 0) return getCss('--missed');
      if (metric(node, 'helpful_count') > 0) return getCss('--helpful');
      if (metric(node, 'hotness_score') > 0 || metric(node, 'recall_count') > 0) return getCss('--hot');
      return getCss('--quiet');
    }

    function nodeRadius(node) {
      return Math.max(6, Math.min(22, 6 + Math.sqrt(node.graph_score || 0) * 2.2));
    }

    function getCss(name) {
      return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }

    function relationshipGroup(node, selected) {
      if (!selected) return 'correlated';
      if (node.id === selected.id) return 'selected';
      if ((selected.parents || []).includes(node.id) || (node.load_next || []).includes(selected.id)) {
        return 'upstream';
      }
      if ((selected.load_next || []).includes(node.id) || (node.parents || []).includes(selected.id)) {
        return 'load_next';
      }
      if ((selected.related || []).includes(node.id) || (node.related || []).includes(selected.id)) {
        return 'related';
      }
      return 'correlated';
    }

    function drilldownColumns(nodes) {
      const selected = selectedMemoryFor(nodes);
      const definitions = [
        ['upstream', 'Upstream'],
        ['selected', 'Selected'],
        ['load_next', 'Load next'],
        ['related', 'Related'],
        ['correlated', 'Other correlated'],
      ];
      return definitions.map(([key, label]) => {
        const bucket = sortedNodes(nodes.filter(node => relationshipGroup(node, selected) === key));
        return { key, label, nodes: bucket };
      }).filter(column => column.nodes.length > 0);
    }

    function drilldownLabelIds(nodes) {
      if (state.graphMode !== 'drilldown') return null;
      const selected = selectedMemoryFor(nodes);
      const ids = new Set();
      if (selected) ids.add(selected.id);
      const budgets = {
        upstream: 3,
        selected: 1,
        load_next: 7,
        related: 4,
        correlated: 2,
      };
      for (const column of drilldownColumns(nodes)) {
        const limit = budgets[column.key] || 2;
        column.nodes
          .slice()
          .sort((a, b) => {
            if (a.id === selected?.id) return -1;
            if (b.id === selected?.id) return 1;
            return (graphScoreForLabel(b) - graphScoreForLabel(a)) || a.id.localeCompare(b.id);
          })
          .slice(0, limit)
          .forEach(node => ids.add(node.id));
      }
      return ids;
    }

    function columnX(index, count, width) {
      if (count <= 1) return width / 2;
      const inset = width < 760 ? 86 : 132;
      return inset + index * ((width - inset * 2) / (count - 1));
    }

    function drilldownLaneCount(column, width, columnCount) {
      if (column.nodes.length <= 6) return 1;
      const averageColumnWidth = Math.max(120, (width - 224) / Math.max(columnCount, 1));
      const availableLanes = Math.max(1, Math.floor(averageColumnWidth / 74));
      return Math.min(3, availableLanes, Math.ceil(column.nodes.length / 6));
    }

    function layoutDrilldown(nodes, width, height) {
      const columns = drilldownColumns(nodes);
      const result = new Map();
      columns.forEach((column, columnIndex) => {
        const baseX = columnX(columnIndex, columns.length, width);
        const laneCount = drilldownLaneCount(column, width, columns.length);
        const rowCount = Math.ceil(column.nodes.length / laneCount);
        const laneSpacing = Math.min(92, Math.max(62, (width / Math.max(columns.length, 1)) * 0.28));
        column.nodes.forEach((node, index) => {
          const lane = index % laneCount;
          const row = Math.floor(index / laneCount);
          const x = baseX + (lane - (laneCount - 1) / 2) * laneSpacing;
          const y = 150 + (row + 0.5) * ((height - 280) / Math.max(rowCount, 1));
          const labelSide = x > width * 0.64 ? 'left' : 'right';
          result.set(node.id, { x, y, layer: column.key, labelSide });
        });
      });
      return result;
    }

    function layoutInit(nodes, width, height) {
      const result = new Map();
      const columns = width >= 760 ? 2 : 1;
      const rows = Math.ceil(nodes.length / columns);
      nodes.forEach((node, index) => {
        const column = index % columns;
        const row = Math.floor(index / columns);
        const x = columns === 1 ? width / 2 : width * (column === 0 ? 0.32 : 0.68);
        const y = 110 + (row + 0.5) * ((height - 190) / Math.max(rows, 1));
        result.set(node.id, { x, y, layer: 'init' });
      });
      return result;
    }

    function layout(nodes, width, height) {
      if (state.graphMode === 'init') return layoutInit(nodes, width, height);
      if (state.graphMode === 'drilldown') return layoutDrilldown(nodes, width, height);
      const groups = new Map();
      const layerOrder = ['init', 'abstract', 'detailed', 'leaf'];
      for (const node of nodes) {
        const layer = layerOrder.includes(node.layer) ? node.layer : 'other';
        if (!groups.has(layer)) groups.set(layer, []);
        groups.get(layer).push(node);
      }
      const layers = [...layerOrder, 'other'].filter(layer => groups.has(layer));
      const result = new Map();
      layers.forEach((layer, layerIndex) => {
        const bucket = sortedNodes(groups.get(layer));
        const x = layers.length === 1 ? width / 2 : 90 + layerIndex * ((width - 240) / (layers.length - 1));
        bucket.forEach((node, index) => {
          const y = 56 + (index + 0.5) * ((height - 112) / Math.max(bucket.length, 1));
          result.set(node.id, { x, y, layer });
        });
      });
      return result;
    }

    function drawDrilldownBands(svg, nodes, width, height) {
      if (state.graphMode !== 'drilldown') return;
      const columns = drilldownColumns(nodes);
      const spacing = columns.length > 1
        ? columnX(1, columns.length, width) - columnX(0, columns.length, width)
        : Math.min(280, width * 0.56);
      columns.forEach((column, index) => {
        const x = columnX(index, columns.length, width);
        const band = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        const bandWidth = Math.max(120, Math.min(260, spacing * 0.74));
        band.setAttribute('x', x - bandWidth / 2);
        band.setAttribute('y', 116);
        band.setAttribute('width', bandWidth);
        band.setAttribute('height', Math.max(180, height - 216));
        band.setAttribute('rx', 26);
        band.setAttribute('class', `drilldownBand ${column.key}`);
        svg.appendChild(band);
      });
    }

    function drawDrilldownHeaders(svg, nodes, width) {
      if (state.graphMode !== 'drilldown') return;
      const columns = drilldownColumns(nodes);
      columns.forEach((column, index) => {
        const x = columnX(index, columns.length, width);
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');

        const headerText = `${column.label} (${column.nodes.length})`;
        const headerWidth = Math.max(108, headerText.length * 7.2 + 28);
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', x - headerWidth / 2);
        rect.setAttribute('y', 64);
        rect.setAttribute('width', headerWidth);
        rect.setAttribute('height', 24);
        rect.setAttribute('rx', 12);
        rect.setAttribute('class', 'labelBox drilldownHeader');
        group.appendChild(rect);

        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', x);
        text.setAttribute('y', 80);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('class', 'label');
        text.textContent = headerText;
        group.appendChild(text);
        svg.appendChild(group);
      });
    }

    function edgePath(source, target) {
      const dx = target.x - source.x;
      const curve = Math.max(54, Math.min(180, Math.abs(dx) * 0.48));
      const c1 = source.x + (dx >= 0 ? curve : -curve);
      const c2 = target.x - (dx >= 0 ? curve : -curve);
      return `M ${source.x} ${source.y} C ${c1} ${source.y}, ${c2} ${target.y}, ${target.x} ${target.y}`;
    }

    function drawGraph(nodes) {
      const svg = document.getElementById('graph');
      const rect = svg.getBoundingClientRect();
      const width = Math.max(480, rect.width || 900);
      const height = Math.max(420, rect.height || 560);
      svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
      svg.innerHTML = '';
      const nodeSet = new Set(nodes.map(node => node.id));
      const positions = layout(nodes, width, height);
      const visibleEdgeCount = DATA.edges.filter(edge => nodeSet.has(edge.source) && nodeSet.has(edge.target)).length;
      const edges = graphEdges(nodeSet);
      const labelIds = drilldownLabelIds(nodes);
      drawDrilldownBands(svg, nodes, width, height);
      drawDrilldownHeaders(svg, nodes, width);

      for (const edge of edges) {
        const source = positions.get(edge.source);
        const target = positions.get(edge.target);
        if (!source || !target) continue;
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        line.setAttribute('d', edgePath(source, target));
        line.setAttribute('fill', 'none');
        const selectedClass = state.selectedId && (edge.source === state.selectedId || edge.target === state.selectedId) ? ' selected' : '';
        line.setAttribute('class', `edge ${edge.type}${selectedClass}`);
        line.setAttribute('stroke', edge.type === 'load_next' ? getCss('--load') : getCss('--related'));
        line.setAttribute('stroke-width', selectedClass ? '2.2' : edge.type === 'load_next' ? '1.55' : '1');
        if (edge.type !== 'load_next') line.setAttribute('stroke-dasharray', '5 5');
        svg.appendChild(line);
      }

      nodes.forEach((node, index) => {
        const pos = positions.get(node.id);
        if (!pos) return;
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        const selectedNode = state.selectedId === node.id;
        group.setAttribute('class', `node${selectedNode ? ' selectedNode' : ''}`);
        group.addEventListener('click', () => selectMemory(node.id));

        const radius = nodeRadius(node);
        if (selectedNode) {
          const halo = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
          halo.setAttribute('cx', pos.x);
          halo.setAttribute('cy', pos.y);
          halo.setAttribute('r', radius + 10);
          halo.setAttribute('class', 'nodeHalo');
          group.appendChild(halo);
        }

        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', pos.x);
        circle.setAttribute('cy', pos.y);
        circle.setAttribute('r', radius);
        circle.setAttribute('fill', nodeColor(node));
        circle.setAttribute('stroke', selectedNode ? '#111827' : 'rgba(255,255,255,0.92)');
        circle.setAttribute('stroke-width', selectedNode ? '3.2' : '1.6');
        group.appendChild(circle);

        const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
        title.textContent = `${node.id}\nrecall=${metric(node, 'recall_count')} helpful=${metric(node, 'helpful_count')} missed=${metric(node, 'missed_recall_count')}`;
        group.appendChild(title);

        if (shouldLabel(node, index, labelIds)) {
          const label = state.graphMode === 'drilldown' ? compactDrilldownLabel(node.id) : compactLabel(node.id);
          const labelWidth = Math.min(selectedNode ? 230 : 178, Math.max(42, label.length * 6.4 + 14));
          const placeLeft = pos.labelSide === 'left' || (pos.labelSide !== 'right' && pos.x + radius + labelWidth + 16 > width);
          const rectX = placeLeft
            ? pos.x - radius - labelWidth - 9
            : pos.x + radius + 7;
          const labelX = rectX + 5;
          const labelY = pos.y - 10;
          const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
          rect.setAttribute('x', rectX);
          rect.setAttribute('y', labelY - 2);
          rect.setAttribute('width', labelWidth);
          rect.setAttribute('height', 20);
          rect.setAttribute('rx', 10);
          rect.setAttribute('class', `labelBox${selectedNode ? ' featuredLabelBox' : ''}`);
          group.appendChild(rect);

          const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
          text.setAttribute('x', labelX);
          text.setAttribute('y', labelY + 13);
          text.setAttribute('class', `label${selectedNode ? ' featuredLabel' : ''}`);
          text.textContent = label;
          group.appendChild(text);
        }

        svg.appendChild(group);
      });

      document.getElementById('graphStatus').textContent =
        state.graphMode === 'init'
          ? `Start with ${nodes.length} init memories. Click one to drill into its neighbors, then keep clicking to go deeper.`
          : state.graphMode === 'drilldown' && selectedMemoryFor(nodes)
          ? `Layer drilldown for ${compactLabel(selectedMemoryFor(nodes).id)}: showing ${nodes.length} correlated memories and ${edges.length} direct edges. Click any node to make it the center.`
          : `Showing ${nodes.length} of ${filteredNodes().length} matching memories and ${edges.length} of ${visibleEdgeCount} visible edges. Use the table for the full set.`;
    }

    function renderStats(nodes) {
      const totals = nodes.reduce((acc, node) => {
        acc.recall += metric(node, 'recall_count');
        acc.selected += metric(node, 'selected_count');
        acc.helpful += metric(node, 'helpful_count');
        acc.missed += metric(node, 'missed_recall_count');
        return acc;
      }, { recall: 0, selected: 0, helpful: 0, missed: 0 });
      const cards = [
        ['Memories', nodes.length],
        ['Graph nodes', graphNodes(nodes).length],
        ['Recall', totals.recall],
        ['Selected', totals.selected],
        ['Helpful', totals.helpful],
        ['Missed', totals.missed],
      ];
      document.getElementById('stats').innerHTML = cards.map(([label, value]) =>
        `<div class="stat"><b>${value}</b><span>${label}</span></div>`
      ).join('');
    }

    function renderTable(nodes) {
      const rows = sortedNodes(nodes).map(node => {
        const selected = state.selectedId === node.id ? ' class="selected"' : '';
        const lastUsed = formatTimestamp(node.metrics.last_used_at);
        return `<tr${selected} data-id="${node.id}">
          <td><div class="memoryId">${node.id}</div><div class="pill" title="${node.metrics.last_used_at || ''}">${lastUsed === 'none' ? 'never used' : lastUsed}</div></td>
          <td>${metric(node, 'recall_count')}</td>
          <td>${metric(node, 'selected_count')}</td>
          <td>${metric(node, 'helpful_count')}</td>
          <td>${metric(node, 'missed_recall_count')}</td>
          <td>${metric(node, 'hotness_score')}</td>
          <td><span class="pill">${node.layer}</span></td>
          <td><span class="pill">${node.status}</span></td>
        </tr>`;
      }).join('');
      const tbody = document.getElementById('memoryRows');
      tbody.innerHTML = rows || '<tr><td colspan="8">No memories match the current filters.</td></tr>';
      tbody.querySelectorAll('tr[data-id]').forEach(row => {
        row.addEventListener('click', () => selectMemory((row as HTMLElement).dataset.id || ''));
      });
    }

    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>"']/g, char => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      }[char]));
    }

    function normalizeRepoPath(value) {
      let text = String(value || '').trim();
      while (text.startsWith('./')) {
        text = text.slice(2);
      }
      return text;
    }

    function urlish(value) {
      return /^[a-z][a-z0-9+.-]*:/i.test(value);
    }

    function repoPathFor(value) {
      const text = normalizeRepoPath(value);
      if (!text || urlish(text)) return text;
      const workspaceRoot = String(DATA.metadata.workspace_root || '').replace(/\/+$/, '');
      if (workspaceRoot && text.startsWith(`${workspaceRoot}/`)) {
        return normalizeRepoPath(text.slice(workspaceRoot.length + 1));
      }
      return text;
    }

    function encodePathSegments(path) {
      return path.split('/').map(part => encodeURIComponent(part)).join('/');
    }

    function absolutePathFor(value) {
      const text = repoPathFor(value);
      if (!text) return '';
      if (urlish(text)) return text;
      if (text.startsWith('/')) return text;
      const workspaceRoot = String(DATA.metadata.workspace_root || '').replace(/\/+$/, '');
      return workspaceRoot ? `${workspaceRoot}/${text}` : text;
    }

    function fileUrlFor(value) {
      const repoPath = repoPathFor(value);
      if (!repoPath) return '';
      if (urlish(repoPath)) return repoPath;
      const generatedFileLinks = DATA.metadata.file_links || {};
      if (generatedFileLinks[repoPath]) return generatedFileLinks[repoPath];
      const generatedRawLinks = DATA.metadata.file_raw_links || {};
      if (generatedRawLinks[repoPath]) return generatedRawLinks[repoPath];
      const fileLinkBase = String(DATA.metadata.file_link_base || '').replace(/^\/+|\/+$/g, '');
      if (fileLinkBase && !repoPath.startsWith('/')) {
        return `${fileLinkBase}/${encodePathSegments(repoPath)}`;
      }
      const path = absolutePathFor(repoPath);
      if (urlish(path)) return path;
      if (path.startsWith('/')) {
        return `file://${path.split('/').map((part, index) => index === 0 ? '' : encodeURIComponent(part)).join('/')}`;
      }
      return encodeURI(path);
    }

    function rawFileUrlFor(value) {
      const repoPath = repoPathFor(value);
      if (!repoPath) return '';
      if (urlish(repoPath)) return repoPath;
      const generatedRawLinks = DATA.metadata.file_raw_links || {};
      if (generatedRawLinks[repoPath]) return generatedRawLinks[repoPath];
      return fileUrlFor(repoPath);
    }

    function list(values) {
      return values && values.length ? values.map(value => `<span class="pill">${escapeHtml(value)}</span>`).join('') : '<span class="pill">none</span>';
    }

    function fileLink(value, className = 'fileLink') {
      const text = repoPathFor(value);
      if (!text) return '<span class="pill">none</span>';
      const href = fileUrlFor(text);
      const rawHref = rawFileUrlFor(text);
      return `<a class="${className}" href="${escapeHtml(href)}" data-file-link="1" data-file-raw-href="${escapeHtml(rawHref)}" data-file-path="${escapeHtml(text)}" target="_blank" rel="noopener noreferrer" title="Preview file content"><code>${escapeHtml(text)}</code></a>`;
    }

    function fileList(values) {
      return values && values.length ? values.map(value => fileLink(value, 'pill fileLink')).join('') : '<span class="pill">none</span>';
    }

    function setFilePreview(path, rawHref, previewHref, bodyHtml, statusText = '') {
      const preview = document.getElementById('filePreview');
      if (!preview) return;
      preview.hidden = false;
      preview.innerHTML = `
        <div class="filePreviewHead">
          <strong>${escapeHtml(path)}</strong>
          <span>
            ${statusText ? `<span>${escapeHtml(statusText)}</span>` : ''}
            <a class="filePreviewAction" href="${escapeHtml(previewHref || rawHref)}" target="_blank" rel="noopener noreferrer">Open raw</a>
            <button class="filePreviewAction" type="button" data-close-file-preview="1">Close</button>
          </span>
        </div>
        ${bodyHtml}
      `;
      const closeButton = preview.querySelector('[data-close-file-preview]');
      if (closeButton) {
        closeButton.addEventListener('click', () => {
          preview.hidden = true;
          preview.innerHTML = '';
        });
      }
    }

    function isMarkdownPath(path) {
      return /\.(md|markdown)$/i.test(String(path || '').split(/[?#]/)[0]);
    }

    function renderInlineMarkdown(text) {
      let rendered = escapeHtml(text);
      rendered = rendered.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
      rendered = rendered.replace(/`([^`]+)`/g, '<code>$1</code>');
      rendered = rendered.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
      rendered = rendered.replace(/__([^_]+)__/g, '<strong>$1</strong>');
      rendered = rendered.replace(/\*([^*]+)\*/g, '<em>$1</em>');
      return rendered;
    }

    function renderMarkdown(text) {
      const lines = String(text || '').replace(/\r\n/g, '\n').split('\n');
      const output = [];
      let inCode = false;
      let codeLines = [];
      let listType = '';

      function closeList() {
        if (!listType) return;
        output.push(`</${listType}>`);
        listType = '';
      }

      for (const line of lines) {
        if (line.startsWith('```')) {
          if (inCode) {
            output.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`);
            codeLines = [];
            inCode = false;
          } else {
            closeList();
            inCode = true;
            codeLines = [];
          }
          continue;
        }

        if (inCode) {
          codeLines.push(line);
          continue;
        }

        const stripped = line.trim();
        if (!stripped) {
          closeList();
          continue;
        }

        const heading = stripped.match(/^(#{1,6})\s+(.+)$/);
        if (heading) {
          closeList();
          const level = heading[1].length;
          output.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
          continue;
        }

        if (/^(-{3,}|\*{3,}|_{3,})$/.test(stripped)) {
          closeList();
          output.push('<hr>');
          continue;
        }

        const unordered = stripped.match(/^[-*]\s+(.+)$/);
        if (unordered) {
          if (listType !== 'ul') {
            closeList();
            output.push('<ul>');
            listType = 'ul';
          }
          output.push(`<li>${renderInlineMarkdown(unordered[1])}</li>`);
          continue;
        }

        const ordered = stripped.match(/^\d+\.\s+(.+)$/);
        if (ordered) {
          if (listType !== 'ol') {
            closeList();
            output.push('<ol>');
            listType = 'ol';
          }
          output.push(`<li>${renderInlineMarkdown(ordered[1])}</li>`);
          continue;
        }

        const quote = stripped.match(/^>\s?(.+)$/);
        if (quote) {
          closeList();
          output.push(`<blockquote>${renderInlineMarkdown(quote[1])}</blockquote>`);
          continue;
        }

        closeList();
        output.push(`<p>${renderInlineMarkdown(stripped)}</p>`);
      }

      if (inCode) output.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`);
      closeList();
      return output.join('\n');
    }

    function renderFileContent(path, text) {
      if (isMarkdownPath(path)) {
        return `<div class="markdownPreview">${renderMarkdown(text || '(empty file)')}</div>`;
      }
      return `<pre>${escapeHtml(text || '(empty file)')}</pre>`;
    }

    async function previewFile(rawHref, path, previewHref = '') {
      setFilePreview(path, rawHref, previewHref, '<pre>Loading file content...</pre>');
      try {
        const response = await fetch(rawHref);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const text = await response.text();
        setFilePreview(path, rawHref, previewHref, renderFileContent(path, text));
      } catch (error) {
        setFilePreview(
          path,
          rawHref,
          previewHref,
          `<pre>Could not load this file in the dashboard preview.\n${escapeHtml(error instanceof Error ? error.message : String(error))}</pre>`,
          'preview failed'
        );
      }
    }

    function bindFileLinks() {
      const details = document.getElementById('details');
      if (!details) return;
      details.querySelectorAll('a[data-file-link]').forEach(link => {
        link.addEventListener('click', event => {
          const anchor = link as HTMLAnchorElement;
          const previewHref = anchor.getAttribute('href') || '';
          const rawHref = anchor.dataset.fileRawHref || previewHref;
          if (!rawHref || rawHref.startsWith('file:')) return;
          event.preventDefault();
          previewFile(rawHref, anchor.dataset.filePath || anchor.textContent || rawHref, previewHref);
        });
      });
    }

    function routeList(routes) {
      if (!routes || !routes.length) return '<p class="desc">No common route data recorded.</p>';
      return `<ul class="routes">${routes.map(item => `<li><code>${item.route}</code> (${
        item.count
      })</li>`).join('')}</ul>`;
    }

    function renderDetails(node) {
      if (!node) {
        document.getElementById('details').innerHTML = '<p class="desc">Select a memory from the graph or table.</p>';
        return;
      }
      document.getElementById('details').innerHTML = `
        <h3>${node.id}</h3>
        <p class="desc">${node.description || 'No description recorded.'}</p>
        <dl>
          <dt>Recall frequency</dt><dd>${metric(node, 'recall_count')}</dd>
          <dt>Selected / helpful</dt><dd>${metric(node, 'selected_count')} / ${metric(node, 'helpful_count')}</dd>
          <dt>Missed / stale / false positive</dt><dd>${metric(node, 'missed_recall_count')} / ${metric(node, 'stale_hit_count')} / ${metric(node, 'false_positive_count')}</dd>
          <dt>Hotness</dt><dd>${metric(node, 'hotness_score')}</dd>
          <dt>Last used</dt><dd title="${node.metrics.last_used_at || ''}">${node.metrics.last_used_at ? formatTimestamp(node.metrics.last_used_at) : 'never'}</dd>
          <dt>Layer / status</dt><dd>${node.layer} / ${node.status}</dd>
          <dt>Freshness</dt><dd>${node.freshness_profile} (${node.freshness_source})</dd>
          <dt>Pattern key</dt><dd>${node.pattern_key || 'none'}</dd>
          <dt>Parents</dt><dd>${list(node.parents)}</dd>
          <dt>Load next</dt><dd>${list(node.load_next)}</dd>
          <dt>Related</dt><dd>${list(node.related)}</dd>
          <dt>Related files</dt><dd>${fileList(node.related_files)}</dd>
          <dt>Path</dt><dd>${fileLink(node.path)}</dd>
        </dl>
        <section id="filePreview" class="filePreview" hidden></section>
        <h3>Common Routes</h3>
        ${routeList(node.metrics.common_routes)}
      `;
      bindFileLinks();
    }

    function renderInitDetails(nodes) {
      const initNodes = sortedNodes(nodes.filter(node => node.layer === 'init'));
      const list = initNodes.map(node => `
        <button class="pill" data-init-id="${node.id}" title="${node.description || node.id}">
          ${compactLabel(node.id)}
        </button>
      `).join('');
      document.getElementById('details').innerHTML = `
        <h3>Start From Init Nodes</h3>
        <p class="desc">Choose an init memory to drill into its immediate parents, children, and related memories. Keep clicking nodes to walk deeper through the memory graph.</p>
        <div>${list || '<span class="pill">No init nodes match the current filters.</span>'}</div>
      `;
      document.querySelectorAll('[data-init-id]').forEach(button => {
        button.addEventListener('click', () => selectMemory((button as HTMLElement).dataset.initId || ''));
      });
    }

    function selectMemory(id) {
      state.selectedId = id;
      state.graphMode = 'drilldown';
      (document.getElementById('graphMode') as HTMLSelectElement).value = state.graphMode;
      renderDetails(byId.get(id));
      render();
    }

    function fillFilters() {
      const layers = ['all', ...new Set(DATA.nodes.map(node => node.layer).sort())];
      const statuses = ['all', ...new Set(DATA.nodes.map(node => node.status).sort())];
      document.getElementById('layerFilter').innerHTML = layers.map(value => `<option value="${value}">Layer: ${value}</option>`).join('');
      document.getElementById('statusFilter').innerHTML = statuses.map(value => `<option value="${value}">Status: ${value}</option>`).join('');
    }

    function render() {
      const nodes = filteredNodes();
      if (state.selectedId && !nodes.some(node => node.id === state.selectedId)) {
        state.selectedId = null;
      }
      if (state.graphMode === 'init') {
        state.selectedId = null;
        renderInitDetails(nodes);
      } else if (!state.selectedId && nodes.length) {
        const first = sortedNodes(nodes)[0];
        state.selectedId = first.id;
        renderDetails(first);
      } else if (state.selectedId) {
        renderDetails(byId.get(state.selectedId));
      } else {
        renderDetails(null);
      }
      renderStats(nodes);
      renderTable(nodes);
      drawGraph(graphNodes(nodes));
    }

    function init() {
      fillFilters();
      document.getElementById('subtitle').textContent =
        `${DATA.metadata.memory_count} memories, ${DATA.metadata.edge_count} edges, ${DATA.metadata.event_count} observability events, window=${DATA.metadata.window_days} days, writer-scope=${DATA.metadata.writer_scope}.`;
      const footer = document.getElementById('footer');
      footer.textContent =
        `Generated at ${formatTimestamp(DATA.metadata.generated_at)} from ${DATA.metadata.root}. Source events: ${formatTimestamp(DATA.metadata.source_min_timestamp)} to ${formatTimestamp(DATA.metadata.source_max_timestamp)}.`;
      footer.title =
        `UTC generated_at=${DATA.metadata.generated_at}; source_min_timestamp=${DATA.metadata.source_min_timestamp || 'none'}; source_max_timestamp=${DATA.metadata.source_max_timestamp || 'none'}`;
      const nodeLimit = document.getElementById('nodeLimit') as HTMLInputElement;
      nodeLimit.max = String(Math.max(12, DATA.metadata.memory_count));
      nodeLimit.value = String(Math.min(DATA.metadata.max_graph_nodes, DATA.metadata.memory_count));
      state.nodeLimit = Number(nodeLimit.value);
      document.getElementById('nodeLimitLabel').textContent = `${state.nodeLimit} nodes`;
      document.getElementById('search').addEventListener('input', event => {
        state.query = (event.target as HTMLInputElement).value;
        render();
      });
      document.getElementById('layerFilter').addEventListener('change', event => {
        state.layer = (event.target as HTMLSelectElement).value;
        render();
      });
      document.getElementById('statusFilter').addEventListener('change', event => {
        state.status = (event.target as HTMLSelectElement).value;
        render();
      });
      document.getElementById('sortKey').addEventListener('change', event => {
        state.sortKey = (event.target as HTMLSelectElement).value;
        render();
      });
      document.getElementById('graphMode').addEventListener('change', event => {
        state.graphMode = (event.target as HTMLSelectElement).value as GraphMode;
        if (state.graphMode === 'init') state.selectedId = null;
        render();
      });
      nodeLimit.addEventListener('input', event => {
        state.nodeLimit = Number((event.target as HTMLInputElement).value);
        document.getElementById('nodeLimitLabel').textContent = `${state.nodeLimit} nodes`;
        render();
      });
      document.querySelectorAll('th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
          const key = (th as HTMLElement).dataset.sort || '';
          state.sortKey = numberKeys.has(key) ? key : state.sortKey;
          (document.getElementById('sortKey') as HTMLSelectElement).value = state.sortKey;
          render();
        });
      });
      render();
      window.addEventListener('resize', render);
    }

    init();
