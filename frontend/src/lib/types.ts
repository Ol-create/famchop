// Mirrors backend/app/schemas.py. Money and quantities arrive as decimal strings, e.g. "1500.00".

export type Role = "admin" | "member";
export type AgeGroup = "child" | "teen" | "adult" | "elderly";

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  age_group: AgeGroup;
  dislikes: string | null;
  family_id: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export type Member = Omit<User, "family_id">;

export interface Family {
  id: number;
  name: string;
  invite_code: string;
  wallet_balance: string;
  members: Member[];
}

export interface Price {
  id: number;
  item: string;
  unit: string;
  price: string | null;
  updated_at: string;
}

export type TransactionType = "fund" | "release" | "spend" | "refund";

export interface Transaction {
  id: number;
  type: TransactionType;
  amount: string;
  note: string | null;
  user_name: string | null;
  errand_id: number | null;
  created_at: string;
}

export interface Wallet {
  balance: string;
  transactions: Transaction[];
}

export interface NutritionAnalysis {
  priorities: string[];
  focus_foods: string[];
  tips: string[];
  disclaimer: string;
}

export interface MenuDay {
  day: string;
  breakfast: string;
  lunch: string;
  dinner: string;
}

export interface PlanItem {
  id: number;
  item: string;
  unit: string;
  quantity: string;
  unit_price: string | null;
  subtotal: string;
}

export interface Plan {
  id: number;
  status: "draft" | "approved";
  budget: string;
  total_cost: string;
  remaining: string;
  over_budget: boolean;
  unpriced_items: string[];
  notes: string | null;
  pantry: string | null;
  menu: MenuDay[];
  nutrition: {
    score: { protein: number; carbs: number; vegetables: number; fruit: number };
    note: string;
    tips: string[];
  } | null;
  swaps: { from_item: string; to_item: string; reason: string }[];
  items: PlanItem[];
  created_at: string;
  disclaimer: string;
}

export type ErrandStatus = "assigned" | "in_progress" | "completed";

export interface ErrandItem {
  id: number;
  item: string;
  unit: string;
  quantity: string;
  unit_price: string | null;
  planned_cost: string;
  bought: boolean;
  actual_price: string | null;
}

export interface Errand {
  id: number;
  plan_id: number;
  status: ErrandStatus;
  assigned_to: { id: number; name: string };
  assigned_by: { id: number; name: string } | null;
  market: string | null;
  released_amount: string;
  planned_total: string;
  bought_count: number;
  item_count: number;
  spent_so_far: string;
  actual_spent: string | null;
  change: string | null;
  items: ErrandItem[];
  created_at: string;
  completed_at: string | null;
}
