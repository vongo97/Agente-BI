'use client';

import React, { useState } from "react";
import { Edit2, Check, X, ArrowLeft, Play, User, Award, ShieldAlert, Cpu } from "lucide-react";

interface Agent {
  name: string;
  role: string;
  description: string;
  personality: string;
}

interface SimAgentConfigProps {
  agents: Agent[];
  onChange: (updatedAgents: Agent[]) => void;
  onBack: () => void;
  onStart: () => void;
  loading?: boolean;
}

export function SimAgentConfig({
  agents,
  onChange,
  onBack,
  onStart,
  loading = false,
}: SimAgentConfigProps) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<Agent>({
    name: "",
    role: "",
    description: "",
    personality: ""
  });

  const handleEditClick = (idx: number, agent: Agent) => {
    setEditingIndex(idx);
    setEditForm({ ...agent });
  };

  const handleCancel = () => {
    setEditingIndex(null);
  };

  const handleSave = (idx: number) => {
    const updated = [...agents];
    updated[idx] = { ...editForm };
    onChange(updated);
    setEditingIndex(null);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setEditForm(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <div className="space-y-6">
      {/* Cabecera y descripción */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-bi-s0 border border-bi-border rounded-lg p-5">
        <div className="space-y-1">
          <h3 className="text-sm font-bold text-bi-text-1 flex items-center space-x-2">
            <Cpu className="w-4 h-4 text-purple-400" />
            <span>Configuración de Enjambre Contextual (Swarm Config)</span>
          </h3>
          <p className="text-xs text-bi-text-2 max-w-2xl leading-relaxed">
            Estos son los perfiles psicológicos y roles que MiroFish ha diseñado a medida para simular el escenario. Edita sus personalidades, descripciones y roles tácticos antes de iniciar el debate.
          </p>
        </div>
        <div className="flex items-center space-x-3 shrink-0">
          <button
            onClick={onBack}
            className="flex items-center space-x-1.5 py-1.5 px-3 bg-bi-s1 border border-bi-border hover:bg-bi-s2 text-bi-text-1 rounded-md text-xs font-semibold transition-all"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Atrás</span>
          </button>
          <button
            onClick={onStart}
            disabled={loading || agents.length === 0}
            className="flex items-center space-x-1.5 py-1.5 px-4 bg-purple-600 hover:bg-purple-700 disabled:opacity-55 text-white rounded-md text-xs font-semibold shadow-sm transition-all active:scale-[0.98]"
          >
            <Play className="w-3.5 h-3.5" />
            <span>{loading ? "Simulando..." : "Iniciar Debate"}</span>
          </button>
        </div>
      </div>

      {/* Grid de Tarjetas de Agentes */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {agents.map((agent, idx) => {
          const isEditing = editingIndex === idx;

          return (
            <div
              key={idx}
              className={`flex flex-col justify-between bg-bi-s0 border ${
                isEditing ? "border-purple-500 shadow-purple-500/10 shadow-md" : "border-bi-border"
              } rounded-lg p-5 transition-all`}
              style={{
                boxShadow: isEditing ? "0 0 12px 1px rgba(168, 85, 247, 0.12)" : "none"
              }}
            >
              {isEditing ? (
                /* Formulario de Edición de Tarjeta */
                <div className="space-y-4 flex-1">
                  <div className="flex items-center justify-between border-b border-bi-border pb-2">
                    <span className="text-[10px] font-bold text-purple-400 uppercase tracking-wider">Editando Analista</span>
                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => handleSave(idx)}
                        className="p-1 hover:bg-teal-500/20 text-teal-400 rounded transition-colors"
                        title="Guardar Cambios"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                      <button
                        onClick={handleCancel}
                        className="p-1 hover:bg-red-500/20 text-red-400 rounded transition-colors"
                        title="Descartar"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                  
                  <div className="space-y-3">
                    <div>
                      <label className="block text-[10px] font-bold text-bi-text-2 uppercase mb-1">Nombre</label>
                      <input
                        type="text"
                        name="name"
                        value={editForm.name}
                        onChange={handleInputChange}
                        className="w-full bg-bi-canvas border border-bi-border focus:border-purple-500 rounded-md px-2.5 py-1 text-xs text-bi-text-1 focus:outline-none"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-[10px] font-bold text-bi-text-2 uppercase mb-1">Rol Táctico</label>
                      <input
                        type="text"
                        name="role"
                        value={editForm.role}
                        onChange={handleInputChange}
                        className="w-full bg-bi-canvas border border-bi-border focus:border-purple-500 rounded-md px-2.5 py-1 text-xs text-bi-text-1 focus:outline-none"
                      />
                    </div>

                    <div>
                      <label className="block text-[10px] font-bold text-bi-text-2 uppercase mb-1">Psicología / Personalidad</label>
                      <input
                        type="text"
                        name="personality"
                        value={editForm.personality}
                        onChange={handleInputChange}
                        className="w-full bg-bi-canvas border border-bi-border focus:border-purple-500 rounded-md px-2.5 py-1 text-xs text-bi-text-1 focus:outline-none"
                        placeholder="Ej. Riguroso, Cínico, Escéptico"
                      />
                    </div>

                    <div>
                      <label className="block text-[10px] font-bold text-bi-text-2 uppercase mb-1">Instrucciones / Foco</label>
                      <textarea
                        name="description"
                        value={editForm.description}
                        onChange={handleInputChange}
                        rows={3}
                        className="w-full bg-bi-canvas border border-bi-border focus:border-purple-500 rounded-md px-2.5 py-1.5 text-xs text-bi-text-1 focus:outline-none resize-none"
                      />
                    </div>
                  </div>
                </div>
              ) : (
                /* Vista Normal de Tarjeta */
                <div className="flex flex-col h-full justify-between space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-2">
                        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-purple-500/15 border border-purple-500/20">
                          <User className="w-3.5 h-3.5 text-purple-400" />
                        </div>
                        <div>
                          <div className="text-xs font-bold text-bi-text-1">{agent.name}</div>
                          <div className="text-[10px] text-bi-text-2 font-medium">{agent.role}</div>
                        </div>
                      </div>
                      <button
                        onClick={() => handleEditClick(idx, agent)}
                        className="p-1 text-bi-text-2 hover:text-purple-400 hover:bg-bi-s1 rounded transition-colors"
                        title="Editar Perfil"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    {/* Personalidad Badge */}
                    <div className="flex items-center space-x-1 bg-bi-s1 border border-bi-border rounded-md px-2 py-1 text-[10px] text-bi-text-2 max-w-fit">
                      <Award className="w-3 h-3 text-purple-400" />
                      <span className="font-semibold">{agent.personality}</span>
                    </div>

                    {/* Descripción de rol */}
                    <p className="text-[11px] text-bi-text-2 leading-relaxed italic bg-bi-s0/40 rounded p-2.5 border border-bi-border/40">
                      "{agent.description}"
                    </p>
                  </div>

                  <div className="pt-3 border-t border-bi-border/50 text-[10px] text-bi-text-2/80 flex items-center space-x-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-teal-400" />
                    <span>Listo para el enjambre</span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {agents.length === 0 && (
        <div className="flex flex-col items-center justify-center min-h-[200px] border border-dashed border-bi-border rounded-lg p-6 text-center space-y-2">
          <ShieldAlert className="w-8 h-8 text-bi-text-2/40" />
          <h4 className="text-xs font-bold text-bi-text-1">No se han generado agentes</h4>
          <p className="text-[11px] text-bi-text-2 max-w-xs">
            Regresa a la pestaña anterior y haz click en "Autogenerar Enjambre" para crear analistas dinámicos adaptados a los datos.
          </p>
        </div>
      )}
    </div>
  );
}
