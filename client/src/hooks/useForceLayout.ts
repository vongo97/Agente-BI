import { useEffect, useRef, useState, useCallback } from 'react';

export interface ForceNode {
  id: string;
  label?: string;
  type?: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  fx?: number | null;
  fy?: number | null;
  [key: string]: any;
}

export interface ForceLink {
  source: string;
  target: string;
  relationship?: string;
}

interface ForceLayoutOptions {
  width: number;
  height: number;
  repulsion?: number;      // Fuerza de repulsión entre nodos
  attraction?: number;     // Fuerza de atracción en enlaces
  gravity?: number;        // Fuerza de gravedad hacia el centro
  friction?: number;       // Fricción/Amortiguación (0 a 1)
  restLength?: number;     // Longitud de reposo del resorte
}

export function useForceLayout(
  initialNodes: { id: string; label?: string; type?: string }[],
  initialLinks: ForceLink[],
  options: ForceLayoutOptions
) {
  const {
    width,
    height,
    repulsion = 800,
    attraction = 0.04,
    gravity = 0.015,
    friction = 0.82,
    restLength = 80,
  } = options;

  const [nodes, setNodes] = useState<ForceNode[]>([]);
  const [links, setLinks] = useState<ForceLink[]>([]);
  
  // Referencias para evitar el coste de renderizado y cierres en el loop de animación
  const nodesRef = useRef<ForceNode[]>([]);
  const linksRef = useRef<ForceLink[]>([]);
  const animationFrameRef = useRef<number | null>(null);
  
  // Nodo actualmente arrastrado
  const draggedNodeIdRef = useRef<string | null>(null);

  // Inicializar nodos con posiciones aleatorias en el centro
  useEffect(() => {
    const initializedNodes = initialNodes.map((n) => {
      // Intentar preservar posiciones si el nodo ya existía
      const existing = nodesRef.current.find((prev) => prev.id === n.id);
      if (existing) {
        return { ...existing, label: n.label, type: n.type };
      }
      
      const angle = Math.random() * Math.PI * 2;
      const radius = 20 + Math.random() * 50;
      return {
        ...n,
        x: width / 2 + Math.cos(angle) * radius,
        y: height / 2 + Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
        fx: null,
        fy: null,
      };
    });

    nodesRef.current = initializedNodes;
    linksRef.current = initialLinks;
    
    setNodes(initializedNodes);
    setLinks(initialLinks);
  }, [initialNodes, initialLinks, width, height]);

  // Loop de físicas
  useEffect(() => {
    const tick = () => {
      const currentNodes = [...nodesRef.current];
      const currentLinks = linksRef.current;
      const centerX = width / 2;
      const centerY = height / 2;

      if (currentNodes.length === 0) {
        animationFrameRef.current = requestAnimationFrame(tick);
        return;
      }

      // 1. Repulsión de Coulomb (entre todos los pares de nodos)
      for (let i = 0; i < currentNodes.length; i++) {
        const nodeA = currentNodes[i];
        for (let j = i + 1; j < currentNodes.length; j++) {
          const nodeB = currentNodes[j];
          
          let dx = nodeB.x - nodeA.x;
          let dy = nodeB.y - nodeA.y;
          
          // Evitar división por cero
          if (dx === 0) dx = 0.1;
          
          const distanceSq = dx * dx + dy * dy;
          const distance = Math.sqrt(distanceSq) || 0.1;
          
          // Fuerza inversamente proporcional al cuadrado de la distancia
          const force = repulsion / (distanceSq + 50); // El offset previene fuerzas infinitas
          
          const fx = (dx / distance) * force;
          const fy = (dy / distance) * force;
          
          // Aplicar fuerza opuesta
          nodeA.vx -= fx;
          nodeA.vy -= fy;
          nodeB.vx += fx;
          nodeB.vy += fy;
        }
      }

      // 2. Atracción de resorte de Hooke (nodos enlazados)
      for (const link of currentLinks) {
        const sourceNode = currentNodes.find((n) => n.id === link.source);
        const targetNode = currentNodes.find((n) => n.id === link.target);
        
        if (sourceNode && targetNode) {
          const dx = targetNode.x - sourceNode.x;
          const dy = targetNode.y - sourceNode.y;
          const distance = Math.sqrt(dx * dx + dy * dy) || 0.1;
          
          // Ley de Hooke: fuerza proporcional a la deformación del resorte
          const displacement = distance - restLength;
          const force = displacement * attraction;
          
          const fx = (dx / distance) * force;
          const fy = (dy / distance) * force;
          
          sourceNode.vx += fx;
          sourceNode.vy += fy;
          targetNode.vx -= fx;
          targetNode.vy -= fy;
        }
      }

      // 3. Gravedad al centro y actualizaciones de posición
      for (const node of currentNodes) {
        // Atracción suave al centro del canvas
        const dx = centerX - node.x;
        const dy = centerY - node.y;
        
        node.vx += dx * gravity;
        node.vy += dy * gravity;
        
        // Aplicar fricción/amortiguación
        node.vx *= friction;
        node.vy *= friction;
        
        // Limitar la velocidad máxima para evitar explosiones
        const speed = Math.sqrt(node.vx * node.vx + node.vy * node.vy);
        const maxSpeed = 15;
        if (speed > maxSpeed) {
          node.vx = (node.vx / speed) * maxSpeed;
          node.vy = (node.vy / speed) * maxSpeed;
        }

        // Actualizar coordenadas
        if (node.fx !== null && node.fx !== undefined) {
          node.x = node.fx;
          node.vx = 0;
        } else {
          node.x += node.vx;
        }
        
        if (node.fy !== null && node.fy !== undefined) {
          node.y = node.fy;
          node.vy = 0;
        } else {
          node.y += node.vy;
        }
        
        // Limitar a los bordes del canvas (mantener dentro de un margen)
        const margin = 25;
        node.x = Math.max(margin, Math.min(width - margin, node.x));
        node.y = Math.max(margin, Math.min(height - margin, node.y));
      }

      // Sincronizar referencia y estado
      nodesRef.current = currentNodes;
      setNodes([...currentNodes]);
      
      animationFrameRef.current = requestAnimationFrame(tick);
    };

    animationFrameRef.current = requestAnimationFrame(tick);
    
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [width, height, repulsion, attraction, gravity, friction, restLength]);

  // Lógica de arrastre interactivo de nodos
  const dragStart = useCallback((nodeId: string) => {
    draggedNodeIdRef.current = nodeId;
    const node = nodesRef.current.find((n) => n.id === nodeId);
    if (node) {
      node.fx = node.x;
      node.fy = node.y;
    }
  }, []);

  const dragUpdate = useCallback((x: number, y: number) => {
    const nodeId = draggedNodeIdRef.current;
    if (nodeId) {
      const node = nodesRef.current.find((n) => n.id === nodeId);
      if (node) {
        node.fx = x;
        node.fy = y;
      }
    }
  }, []);

  const dragEnd = useCallback(() => {
    const nodeId = draggedNodeIdRef.current;
    if (nodeId) {
      const node = nodesRef.current.find((n) => n.id === nodeId);
      if (node) {
        node.fx = null;
        node.fy = null;
      }
    }
    draggedNodeIdRef.current = null;
  }, []);

  return {
    nodes,
    links,
    dragStart,
    dragUpdate,
    dragEnd,
  };
}
