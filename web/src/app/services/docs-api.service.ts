import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  ConfirmPayload,
  PanelConfig,
  PaginatedResponse,
  PanelData,
} from '../models/docs';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = 'http://localhost:8000/api';

  getPanels(
    page: number,
    pageSize: number,
  ): Observable<PaginatedResponse<PanelConfig>> {
    return this.http.get<PaginatedResponse<PanelConfig>>(
      `${this.baseUrl}/panels`,
      {
        params: { page: String(page), pageSize: String(pageSize) },
      },
    );
  }

  getPanelData(panelId: string): Observable<PanelData> {
    return this.http.get<PanelData>(`${this.baseUrl}/panels/${panelId}`);
  }

  confirmar(payload: ConfirmPayload): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/confirmar`, payload);
  }

  descartarDeclaracao(numero: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/declaracoes/${numero}`);
  }
}
