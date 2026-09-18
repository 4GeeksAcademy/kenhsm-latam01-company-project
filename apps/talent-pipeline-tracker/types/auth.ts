export type LoginPayload = {
  email: string;
  password: string;
};

export type RegisterPayload = {
  email: string;
  password: string;
  name?: string;
  phone?: string;
  address?: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type ProfileOut = {
  id: string;
  user_id: string;
  name: string | null;
  phone: string | null;
  address: string | null;
};

export type UserRole = "admin" | "manager" | "user";

export type CurrentUser = {
  email: string;
  role: UserRole;
  profile: ProfileOut | null;
};

export type ProfileUpdatePayload = {
  name?: string;
  phone?: string;
  address?: string;
};
