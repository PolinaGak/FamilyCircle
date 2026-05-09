import React, { useEffect, useState, useMemo } from 'react';
import ReactFlow, { Node, Edge, Background, Controls, MiniMap } from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import { familyAPI } from '../api/family';
import { Spin, message, Select, Typography } from 'antd';
import { useAuth } from '../contexts/AuthContext';
import { Handle, Position } from 'reactflow';

interface TreeNodeData {
  id: number;
  first_name: string;
  last_name: string;
  patronymic?: string;
  birth_date?: string;
  death_date?: string;
  gender?: string;
  is_active: boolean;
  generation: number;
  partners: number[];
  user_id?: number;
}

interface TreeEdgeData {
  from: number;
  to: number;
  type: string;
}

const FamilyNode: React.FC<{ data: any }> = ({ data }) => {
  const isActive = data.is_active !== false;
  const containerStyle: React.CSSProperties = {
    padding: '10px 15px',
    borderRadius: '8px',
    background: isActive ? '#f0eaff' : '#e0e0e0',
    border: `2px solid ${isActive ? '#b8a9e8' : '#9e9e9e'}`,
    minWidth: '120px',
    textAlign: 'center',
    fontSize: '14px',
    position: 'relative',
    opacity: isActive ? 1 : 0.7,
  };

  return (
    <div style={containerStyle}>
      <Handle
        type="target"
        position={Position.Bottom}
        style={{ background: '#b8a9e8', width: 8, height: 8 }}
      />
      <Handle
        type="source"
        position={Position.Top}
        style={{ background: '#b8a9e8', width: 8, height: 8 }}
      />
      <div style={{ fontWeight: 'bold' }}>
        {data.last_name} {data.first_name}
      </div>
      {data.birth_date && (
        <div style={{ fontSize: '12px', color: '#666' }}>
          {new Date(data.birth_date).getFullYear()}
          {data.death_date ? ` - ${new Date(data.death_date).getFullYear()}` : ''}
        </div>
      )}
    </div>
  );
};

const nodeTypes = { familyNode: FamilyNode };

const getLayoutedElements = (nodes: Node[], edges: Edge[]) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: 'BT' });

  nodes.forEach((node) => {
    const generation = node.data.generation ?? 0;
    dagreGraph.setNode(node.id, { width: 160, height: 60, rank: generation });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.position = {
      x: nodeWithPosition.x - 80,
      y: nodeWithPosition.y - 30,
    };
  });

  return { nodes, edges };
};

const FamilyTreePage: React.FC = () => {
  const { families, currentFamily, setCurrentFamily, loadUserFamilies } = useAuth();
  const [selectedFamilyId, setSelectedFamilyId] = useState<number | undefined>(currentFamily?.id);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [loading, setLoading] = useState(false);
  const [isLoadingFamilies, setIsLoadingFamilies] = useState(true);

  useEffect(() => {
    const init = async () => {
      setIsLoadingFamilies(true);
      if (families.length === 0) {
        await loadUserFamilies();
      }
      if (families.length > 0 && !selectedFamilyId) {
        const first = families[0];
        setSelectedFamilyId(first.id);
        setCurrentFamily(first);
      }
      setIsLoadingFamilies(false);
    };
    init();
  }, [families.length]);

  useEffect(() => {
    if (!selectedFamilyId) return;
    fetchTree(selectedFamilyId);
  }, [selectedFamilyId]);

  const fetchTree = async (famId: number) => {
    setLoading(true);
    try {
      const response = await familyAPI.getFamilyTree(famId, undefined, true);
      const treeData = response.data;

      const flowNodes: Node[] = treeData.nodes.map((n: TreeNodeData) => ({
        id: n.id.toString(),
        type: 'familyNode',
        position: { x: 0, y: 0 },
        data: n,
      }));

      const flowEdges: Edge[] = treeData.edges
        .filter((e: TreeEdgeData) => e.type === 'son' || e.type === 'daughter')
        .map((e: TreeEdgeData) => ({
          id: `${e.from}-${e.to}`,
          source: e.from.toString(),
          target: e.to.toString(),
          style: { stroke: '#b8a9e8', strokeWidth: 2 },
        }));

      setNodes(flowNodes);
      setEdges(flowEdges);
    } catch (error) {
      message.error('Ошибка загрузки дерева');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleFamilyChange = (familyId: number) => {
    const selected = families.find(f => f.id === familyId);
    if (selected) {
      setSelectedFamilyId(familyId);
      setCurrentFamily(selected);
    }
  };

  const positionedElements = useMemo(
    () => getLayoutedElements(nodes, edges),
    [nodes, edges]
  );

  if (isLoadingFamilies || !selectedFamilyId) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (families.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Typography.Title level={4}>У вас нет семей</Typography.Title>
        <Typography.Text type="secondary">
          Создайте или присоединитесь к семье на главной странице
        </Typography.Text>
      </div>
    );
  }

  return (
    <div style={{ height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '16px 24px', background: '#fff', borderBottom: '1px solid #f0f0f0' }}>
        <Typography.Title level={2} style={{ margin: '0 0 16px 0' }}>
          Семейное древо
        </Typography.Title>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontWeight: 500 }}>Семья:</span>
            <Select
              value={selectedFamilyId}
              onChange={handleFamilyChange}
              style={{ width: 220 }}
              options={families.map(f => ({ value: f.id, label: f.name }))}
            />
          </div>
        </div>
      </div>
      <div style={{ flex: 1 }}>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '50px' }}>
            <Spin size="large" />
          </div>
        ) : (
          <ReactFlow
            nodes={positionedElements.nodes}
            edges={positionedElements.edges}
            nodeTypes={nodeTypes}
            fitView
            attributionPosition="bottom-right"
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        )}
      </div>
    </div>
  );
};

export default FamilyTreePage;