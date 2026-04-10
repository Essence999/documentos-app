import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { rxResource } from '@angular/core/rxjs-interop';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
import { RadioButtonModule } from 'primeng/radiobutton';
import { SkeletonModule } from 'primeng/skeleton';
import { TooltipModule } from 'primeng/tooltip';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ApiService } from '../../services/docs-api.service';
import { Contrato, Declaracao } from '../../models/docs';

// ── Process colour palette (up to 10 distinct processes) ───────────────────
const PROCESS_COLORS = [
  '#3b82f6', // blue
  '#f97316', // orange
  '#22c55e', // green
  '#ef4444', // red
  '#a855f7', // purple
  '#eab308', // yellow
  '#06b6d4', // cyan
  '#ec4899', // pink
  '#84cc16', // lime
  '#14b8a6', // teal
] as const;

// ── Enriched row types (add group-break flag without touching the model) ────
interface ContratoRow {
  item: Contrato;
  groupBreak: boolean; // true → render a divider before this row
}

interface DeclaracaoRow {
  item: Declaracao;
  groupBreak: boolean;
}

@Component({
  selector: 'app-panel-content',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    ButtonModule,
    CheckboxModule,
    RadioButtonModule,
    SkeletonModule,
    TooltipModule,
  ],
  templateUrl: './panel-content.component.html',
  styleUrl: './panel-content.component.css',
})
export class PanelContentComponent {
  readonly panelId = input.required<string>();

  private readonly api = inject(ApiService);
  private readonly confirmationService = inject(ConfirmationService);
  private readonly messageService = inject(MessageService);

  protected readonly SKELETON_ROWS = [1, 2, 3, 4] as const;

  // ── Local state ──────────────────────────────────────────────────────────
  readonly selectedContrato = signal<string | null>(null);
  readonly selectedDeclaracoes = signal<string[]>([]);
  readonly confirming = signal(false);

  readonly canConfirm = computed(
    () =>
      !this.confirming() &&
      this.selectedContrato() !== null &&
      this.selectedDeclaracoes().length > 0,
  );

  // ── Resource ─────────────────────────────────────────────────────────────
  readonly panelDataResource = rxResource({
    request: () => this.panelId(),
    loader: ({ request: id }) => this.api.getPanelData(id),
  });

  // ── Process → colour mapping ──────────────────────────────────────────────
  /**
   * Collects every unique processo ID that appears in this panel (from both
   * contratos and declarações), sorts them for a stable assignment, then maps
   * each to a colour from the fixed palette. Index wraps at 10.
   */
  private readonly processoColorMap = computed<Map<string, string>>(() => {
    const data = this.panelDataResource.value();
    if (!data) return new Map();

    const ids = new Set<string>();
    data.contratos.forEach((c) =>
      c.numeros_processo.forEach((p) => ids.add(p)),
    );
    data.declaracoes.forEach((d) => ids.add(d.numero_processo));

    return new Map(
      [...ids]
        .sort()
        .map((id, i) => [id, PROCESS_COLORS[i % PROCESS_COLORS.length]]),
    );
  });

  // ── Enriched row arrays ───────────────────────────────────────────────────
  readonly contratoRows = computed<ContratoRow[]>(() => {
    const items = this.panelDataResource.value()?.contratos ?? [];
    let prevKey = '';
    return items.map((item, i) => {
      // Group key = first processo (API sorts by min processo already)
      const key = item.numeros_processo[0] ?? '';
      const groupBreak = i > 0 && key !== prevKey;
      prevKey = key;
      return { item, groupBreak };
    });
  });

  readonly declaracaoRows = computed<DeclaracaoRow[]>(() => {
    const items = this.panelDataResource.value()?.declaracoes ?? [];
    let prevProcesso = '';
    return items.map((item, i) => {
      const groupBreak = i > 0 && item.numero_processo !== prevProcesso;
      prevProcesso = item.numero_processo;
      return { item, groupBreak };
    });
  });

  // ── Colour helpers ────────────────────────────────────────────────────────
  /**
   * Hard-stop linear gradient for multi-process contratos.
   * Single process → plain background.
   */
  contratoBarStyle(numeros: string[]): string {
    const colors = numeros.map(
      (n) => this.processoColorMap().get(n) ?? '#94a3b8',
    );
    if (colors.length === 1) return `background: ${colors[0]}`;
    const step = 100 / colors.length;
    const stops = colors
      .map((c, i) => `${c} ${i * step}% ${(i + 1) * step}%`)
      .join(', ');
    return `background: linear-gradient(to bottom, ${stops})`;
  }

  processoColor(numero: string): string {
    return this.processoColorMap().get(numero) ?? '#94a3b8';
  }

  // ── Actions ──────────────────────────────────────────────────────────────
  confirmar(): void {
    const numero_contrato = this.selectedContrato();
    const numeros_declaracao = this.selectedDeclaracoes();
    if (!numero_contrato || !numeros_declaracao.length) return;

    const count = numeros_declaracao.length;
    const plural = count === 1;

    this.confirmationService.confirm({
      message: `Confirmar o contrato <strong>${numero_contrato}</strong> com
        <strong>${count}</strong> declaraç${plural ? 'ão' : 'ões'} selecionada${plural ? '' : 's'}?`,
      header: 'Confirmar Operação',
      icon: 'pi pi-check-circle',
      acceptLabel: 'Confirmar',
      rejectLabel: 'Cancelar',
      defaultFocus: 'reject',
      accept: () => this.executeConfirmar(numero_contrato, numeros_declaracao),
    });
  }

  private executeConfirmar(
    numero_contrato: string,
    numeros_declaracao: string[],
  ): void {
    this.confirming.set(true);
    this.api.confirmar({ numero_contrato, numeros_declaracao }).subscribe({
      next: () => {
        this.selectedContrato.set(null);
        this.selectedDeclaracoes.set([]);
        this.panelDataResource.reload();
        this.messageService.add({
          severity: 'success',
          summary: 'Confirmado',
          detail: 'Operação realizada com sucesso.',
          life: 4000,
        });
        this.confirming.set(false);
      },
      error: () => {
        this.messageService.add({
          severity: 'error',
          summary: 'Erro',
          detail: 'Falha ao confirmar. Tente novamente.',
          life: 5000,
        });
        this.confirming.set(false);
      },
    });
  }

  descartar(numero: string): void {
    this.confirmationService.confirm({
      message: `Deseja realmente descartar a declaração <strong>${numero}</strong>?<br>Esta ação não pode ser desfeita.`,
      header: 'Confirmar Descarte',
      icon: 'pi pi-exclamation-triangle',
      acceptLabel: 'Descartar',
      rejectLabel: 'Cancelar',
      acceptButtonStyleClass: 'p-button-danger',
      defaultFocus: 'reject',
      accept: () => this.executeDescartar(numero),
    });
  }

  private executeDescartar(numero: string): void {
    this.api.descartarDeclaracao(numero).subscribe({
      next: () => {
        this.selectedDeclaracoes.update((prev) =>
          prev.filter((n) => n !== numero),
        );
        this.panelDataResource.reload();
        this.messageService.add({
          severity: 'success',
          summary: 'Descartado',
          detail: `Declaração ${numero} descartada com sucesso.`,
          life: 4000,
        });
      },
      error: () => {
        this.messageService.add({
          severity: 'error',
          summary: 'Erro',
          detail: `Falha ao descartar ${numero}. Tente novamente.`,
          life: 5000,
        });
      },
    });
  }
}
