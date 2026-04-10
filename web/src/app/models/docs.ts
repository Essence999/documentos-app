export interface PanelConfig {
  id: string;
  label: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

export interface Contrato {
  numero_contrato: string;
  descricao?: string;
}

export interface Declaracao {
  numero_declaracao: string;
  descricao?: string;
}

export interface PanelData {
  contratos: Contrato[];
  declaracoes: Declaracao[];
}

export interface ConfirmPayload {
  numero_contrato: string;
  numeros_declaracao: string[];
}
