import React, { useEffect, useState, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import { familyAPI } from '../api/family';
import { Spin, message, Select, Typography, Card } from 'antd';
import { useAuth } from '../contexts/AuthContext';
import { Handle, Position } from 'reactflow'

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
  return (
    <div style={{
      padding: '10px 15px',
      borderRadius: '8px',
      background: '#f0eaff',
      border: '2px solid #b8a9e8',
      minWidth: '120px',
      textAlign: 'center',
      fontSize: '14px',
      position: 'relative', 
    }}>
      
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: '#b8a9e8', width: 8, height: 8 }}
      />
      
      <Handle
        type="source"
        position={Position.Bottom}
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

const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction });

  const nodeWidth = 160;
  const nodeHeight = 60;

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };
  });

  return { nodes, edges };
};

const FamilyTreePage: React.FC = () => {
  const { families, currentFamily, setCurrentFamily, loadUserFamilies } = useAuth();
  const [selectedFamilyId, setSelectedFamilyId] = useState<number | undefined>(currentFamily?.id);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [rootId, setRootId] = useState<number | undefined>();
  const [roots, setRoots] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [isLoadingFamilies, setIsLoadingFamilies] = useState(true);

  // Загружаем семьи при монтировании
  useEffect(() => {
    const loadData = async () => {
      setIsLoadingFamilies(true);
      if (families.length === 0) {
        await loadUserFamilies();
      }
      if (families.length > 0 && !selectedFamilyId) {
        const firstFamily = families[0];
        setSelectedFamilyId(firstFamily.id);
        setCurrentFamily(firstFamily);
      }
      setIsLoadingFamilies(false);
    };
    loadData();
  }, [families.length, loadUserFamilies, setCurrentFamily]);

  // Загружаем дерево при смене семьи
  useEffect(() => {
    if (selectedFamilyId) {
      fetchTree(selectedFamilyId);
      fetchRoots(selectedFamilyId);
    }
  }, [selectedFamilyId]);

  const fetchTree = async (famId: number, rootMemberId?: number) => {
    setLoading(true);
    try {
      const response = await familyAPI.getFamilyTree(famId, rootMemberId);
      const treeData = response.data;
      setRootId(treeData.root_id);

      const flowNodes: Node[] = treeData.nodes.map((n: TreeNodeData) => ({
        id: n.id.toString(),
        type: 'familyNode',
        position: { x: 0, y: 0 },
        data: n,
      }));

      const flowEdges: Edge[] = treeData.edges.map((e: TreeEdgeData) => ({
        id: `${e.from}-${e.to}`,
        source: e.from.toString(),
        target: e.to.toString(),
        label: e.type,
        style: { stroke: '#999' },
      }));

      setNodes(flowNodes);
    const edgeMap = new Map<string, Edge>();
    const priority = (type: string) => {
    if (type === 'son' || type === 'daughter') return 1;
    if (type === 'brother' || type === 'sister') return 2;
    if (type === 'spouse' || type === 'partner') return 3;
    return 4; 
    };

    flowEdges.forEach((edge) => {
    const key = [edge.source, edge.target].sort().join('-'); 
    const existing = edgeMap.get(key);
    if (!existing || priority(edge.label as string) < priority(existing.label as string)) {
        edgeMap.set(key, edge);
    }
    });

    const filteredEdges = Array.from(edgeMap.values());
    setEdges(filteredEdges);
      
    
    } catch (error) {
      message.error('Ошибка загрузки дерева');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRoots = async (famId: number) => {
    try {
      const response = await familyAPI.getTreeRoots(famId);
      setRoots(response.data);
    } catch (error) {
      console.error('Ошибка загрузки корней', error);
    }
  };

  const handleFamilyChange = (familyId: number) => {
    const selected = families.find((f) => f.id === familyId);
    if (selected) {
      setSelectedFamilyId(familyId);
      setCurrentFamily(selected);
    }
  };

  const handleRootChange = (value: number) => {
    if (selectedFamilyId) {
      fetchTree(selectedFamilyId, value);
    }
  };

  const positionedElements = useMemo(
    () => getLayoutedElements(nodes, edges, 'TB'),
    [nodes, edges]
  );

  if (isLoadingFamilies) {
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
    <div style={{ height: 'calc(100vh - 64px)', width: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Шапка с заголовком и выбором семьи */}
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
              options={families.map((f) => ({ value: f.id, label: f.name }))}
            />
          </div>
          {roots.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ fontWeight: 500 }}>Корень дерева:</span>
              <Select
                value={rootId}
                onChange={handleRootChange}
                style={{ width: 250 }}
                showSearch
                filterOption={(input, option) =>
                  String(option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                options={roots.map((root) => ({
                  value: root.id,
                  label: root.name,
                }))}
              />
            </div>
          )}
        </div>
      </div>

      {/* Область дерева */}
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