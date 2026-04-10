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

  // ── Resources ────────────────────────────────────────────────────────────
  readonly panelDataResource = rxResource({
    request: () => this.panelId(),
    loader: ({ request: id }) => this.api.getPanelData(id),
  });

  readonly contratos = computed(
    () => this.panelDataResource.value()?.contratos ?? [],
  );
  readonly declaracoes = computed(
    () => this.panelDataResource.value()?.declaracoes ?? [],
  );

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
      // Use [innerHTML] via acceptIcon trick: escape the numero in message
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
        // Remove from selection if it was selected
        this.selectedDeclaracoes.update((prev) =>
          prev.filter((n) => n !== numero),
        );
        // Reload the panel data to reflect the discard
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
