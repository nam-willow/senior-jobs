import type { ReactNode } from 'react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  width?: number;
}

export function Modal({ open, onClose, children, width = 880 }: ModalProps) {
  if (!open) return null;
  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, background: 'rgba(20,30,25,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 100, padding: 20,
    }}>
      <div onClick={(e) => e.stopPropagation()} style={{
        background: 'var(--cream-50)', borderRadius: 24,
        width, maxWidth: '100%', maxHeight: '92vh', overflow: 'auto',
        boxShadow: 'var(--shadow-lg)',
      }}>
        {children}
      </div>
    </div>
  );
}
