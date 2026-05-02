"use client";
import type { JSX } from "react";
interface CollectionsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  collections: Array<{ name: string; document_count: number; vector_count: number }>;
  onIngest: () => void;
}
export function CollectionsDrawer({ isOpen }: CollectionsDrawerProps): JSX.Element | null {
  if (!isOpen) return null;
  return null;
}
