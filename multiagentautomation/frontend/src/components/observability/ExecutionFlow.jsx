import { useCallback } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Check, Pause, Settings, User } from 'lucide-react';

const nodeTypes = {
  agent: ({ data }) => (
    <div className={`flow-node flow-node--${data.status}`}>
      {data.icon === 'user' && <User size={20} />}
      {data.icon === 'gear' && <Settings size={20} />}
      {data.icon === 'pause' && <Pause size={20} />}
      {data.status === 'done' && (
        <Check size={12} style={{ position: 'absolute', bottom: -4, right: -4, color: 'var(--success)' }} />
      )}
    </div>
  ),
};

const initialNodes = [
  { id: '1', type: 'agent', position: { x: 40, y: 80 }, data: { icon: 'user', status: 'done' } },
  { id: '2', type: 'agent', position: { x: 180, y: 40 }, data: { icon: 'gear', status: 'done' } },
  { id: '3', type: 'agent', position: { x: 320, y: 100 }, data: { icon: 'pause', status: 'pause' } },
  { id: '4', type: 'agent', position: { x: 460, y: 50 }, data: { icon: 'pause', status: 'pause' } },
  { id: '5', type: 'agent', position: { x: 600, y: 90 }, data: { icon: 'gear', status: 'active' } },
];

const initialEdges = [
  { id: 'e1-2', source: '1', target: '2', animated: true },
  { id: 'e2-3', source: '2', target: '3', animated: true },
  { id: 'e3-4', source: '3', target: '4' },
  { id: 'e4-5', source: '4', target: '5', animated: true },
].map((e) => ({
  ...e,
  style: { stroke: 'var(--accent)', strokeWidth: 2 },
  markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--accent)' },
}));

export default function ExecutionFlow() {
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const onNodeClick = useCallback((_, node) => {
    console.info('Selected node:', node.id);
  }, []);

  return (
    <div style={{ width: '100%', height: 360 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        colorMode="dark"
      >
        <Background gap={20} color="var(--border)" />
        <Controls />
        <MiniMap
          nodeColor={() => 'var(--accent)'}
          maskColor="rgba(0,0,0,0.6)"
          style={{ background: 'var(--bg-card)' }}
        />
      </ReactFlow>
    </div>
  );
}
