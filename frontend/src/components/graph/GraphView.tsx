'use client'

import { GraphEdge, GraphNode } from '@/types'

interface GraphViewProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

const WIDTH = 920
const HEIGHT = 560

const nodeStyles: Record<string, { fill: string; stroke: string }> = {
  paper: { fill: '#EEF2FF', stroke: '#4F46E5' },
  concept: { fill: '#ECFDF5', stroke: '#059669' },
  author: { fill: '#FFF7ED', stroke: '#EA580C' },
}

export default function GraphView({ nodes, edges }: GraphViewProps) {
  const nodesById = new Map(nodes.map(node => [node.id, node]))

  if (nodes.length === 0) {
    return (
      <div className="h-[560px] border border-parchment-border rounded-xl flex items-center justify-center text-sm text-muted">
        No graph data yet
      </div>
    )
  }

  const point = (node: GraphNode) => ({
    x: node.x * WIDTH,
    y: node.y * HEIGHT,
  })

  return (
    <div className="border border-parchment-border rounded-xl overflow-hidden bg-parchment/20">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full h-[560px]" role="img">
        <g>
          {edges.map(edge => {
            const source = nodesById.get(edge.source)
            const target = nodesById.get(edge.target)
            if (!source || !target) return null
            const a = point(source)
            const b = point(target)
            return (
              <g key={edge.id}>
                <line
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke="#D1D5DB"
                  strokeWidth={1.4}
                />
              </g>
            )
          })}
        </g>

        <g>
          {nodes.map(node => {
            const p = point(node)
            const style = nodeStyles[node.type] || { fill: '#F3F4F6', stroke: '#6B7280' }
            const radius = node.type === 'paper' ? 15 : 9 + Math.min(node.centrality * 18, 8)
            return (
              <g key={node.id}>
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={radius}
                  fill={style.fill}
                  stroke={style.stroke}
                  strokeWidth={2}
                />
                <text
                  x={p.x + radius + 6}
                  y={p.y + 4}
                  className="fill-navy text-[11px] font-medium"
                >
                  {node.label.length > 34 ? `${node.label.slice(0, 31)}...` : node.label}
                </text>
              </g>
            )
          })}
        </g>
      </svg>
    </div>
  )
}
