"use client";

import { useQuery } from "@tanstack/react-query";
import { api, apiOrNull } from "./api";
import type { Errand, Family, Plan, Price, User, Wallet } from "./types";

export const keys = {
  me: ["me"] as const,
  family: ["family"] as const,
  wallet: ["wallet"] as const,
  prices: ["prices"] as const,
  latestPlan: ["plans", "latest"] as const,
  errands: ["errands"] as const,
  myErrands: ["errands", "mine"] as const,
  errand: (id: number) => ["errands", id] as const,
};

export const useMe = () => useQuery({ queryKey: keys.me, queryFn: () => api<User>("/me") });
export const useFamily = () => useQuery({ queryKey: keys.family, queryFn: () => api<Family>("/family") });
export const useWallet = () => useQuery({ queryKey: keys.wallet, queryFn: () => api<Wallet>("/wallet") });
export const usePrices = () => useQuery({ queryKey: keys.prices, queryFn: () => api<Price[]>("/prices") });
export const useLatestPlan = () =>
  useQuery({ queryKey: keys.latestPlan, queryFn: () => apiOrNull<Plan>("/plans/latest") });
export const useErrands = () => useQuery({ queryKey: keys.errands, queryFn: () => api<Errand[]>("/errands") });
export const useMyErrands = () =>
  useQuery({ queryKey: keys.myErrands, queryFn: () => api<Errand[]>("/errands/mine") });
export const useErrand = (id: number) =>
  useQuery({ queryKey: keys.errand(id), queryFn: () => api<Errand>(`/errands/${id}`) });
