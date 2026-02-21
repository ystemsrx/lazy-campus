import {
  Hexagon, Layers, Wallet, Package,
  BookOpen, Code2, ShoppingBag, Camera, Truck,
  MessageSquare, MapPin, ClipboardList,
  Pencil, Music, Heart, Home, Wrench, Dumbbell,
  GraduationCap, Globe, Coffee, Car, Phone, Utensils,
} from 'lucide-vue-next'
import type { Component } from 'vue'

export interface TaskIconOption {
  name: string
  label: string
  component: Component
  color: string
  bg: string
}

export const TASK_ICON_OPTIONS: TaskIconOption[] = [
  { name: 'Hexagon', label: '默认', component: Hexagon, color: '#8b5cf6', bg: '#f5f3ff' },
  { name: 'Layers', label: '图层', component: Layers, color: '#10b981', bg: '#ecfdf5' },
  { name: 'Wallet', label: '钱包', component: Wallet, color: '#f43f5e', bg: '#fff1f2' },
  { name: 'Package', label: '包裹', component: Package, color: '#f59e0b', bg: '#fffbeb' },
  { name: 'BookOpen', label: '书籍', component: BookOpen, color: '#3b82f6', bg: '#eff6ff' },
  { name: 'Code2', label: '代码', component: Code2, color: '#06b6d4', bg: '#ecfeff' },
  { name: 'ShoppingBag', label: '购物', component: ShoppingBag, color: '#ec4899', bg: '#fdf2f8' },
  { name: 'Camera', label: '拍摄', component: Camera, color: '#f97316', bg: '#fff7ed' },
  { name: 'Truck', label: '配送', component: Truck, color: '#64748b', bg: '#f8fafc' },
  { name: 'MessageSquare', label: '沟通', component: MessageSquare, color: '#0ea5e9', bg: '#f0f9ff' },
  { name: 'MapPin', label: '地点', component: MapPin, color: '#ef4444', bg: '#fef2f2' },
  { name: 'ClipboardList', label: '清单', component: ClipboardList, color: '#14b8a6', bg: '#f0fdfa' },
  { name: 'Pencil', label: '设计/绘图', component: Pencil, color: '#a855f7', bg: '#faf5ff' },
  { name: 'Music', label: '音乐/娱乐', component: Music, color: '#ec4899', bg: '#fdf2f8' },
  { name: 'Heart', label: '医疗/关爱', component: Heart, color: '#f43f5e', bg: '#fff1f2' },
  { name: 'Home', label: '家务/居家', component: Home, color: '#10b981', bg: '#ecfdf5' },
  { name: 'Wrench', label: '维修/DIY', component: Wrench, color: '#78716c', bg: '#fafaf9' },
  { name: 'Dumbbell', label: '运动/健身', component: Dumbbell, color: '#f97316', bg: '#fff7ed' },
  { name: 'GraduationCap', label: '教育/辅导', component: GraduationCap, color: '#3b82f6', bg: '#eff6ff' },
  { name: 'Globe', label: '翻译/国际', component: Globe, color: '#0ea5e9', bg: '#f0f9ff' },
  { name: 'Coffee', label: '餐饮/跑腿', component: Coffee, color: '#92400e', bg: '#fef3c7' },
  { name: 'Car', label: '交通/驾驶', component: Car, color: '#64748b', bg: '#f8fafc' },
  { name: 'Phone', label: '电话/客服', component: Phone, color: '#22c55e', bg: '#f0fdf4' },
  { name: 'Utensils', label: '餐饮/厨房', component: Utensils, color: '#d97706', bg: '#fffbeb' },
]

export function getTaskIcon(name: string | null | undefined): TaskIconOption {
  return TASK_ICON_OPTIONS.find(o => o.name === name) || TASK_ICON_OPTIONS[0]
}
