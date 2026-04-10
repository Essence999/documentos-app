import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { AccordionModule } from 'primeng/accordion';
import { ButtonModule } from 'primeng/button';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { PaginatorModule, PaginatorState } from 'primeng/paginator';
import { SkeletonModule } from 'primeng/skeleton';
import { ToastModule } from 'primeng/toast';
import { ConfirmationService, MessageService } from 'primeng/api';
import { PanelContentComponent } from '../panel-content/panel-content.component';
import { ApiService } from '../../services/docs-api.service';

@Component({
  selector: 'app-accordion-list',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [ConfirmationService, MessageService],
  imports: [
    AccordionModule,
    ButtonModule,
    ConfirmDialogModule,
    PaginatorModule,
    SkeletonModule,
    ToastModule,
    PanelContentComponent,
  ],
  templateUrl: './accordion-list.component.html',
  styleUrl: './accordion-list.component.css',
})
export class AccordionListComponent {
  private readonly api = inject(ApiService);

  protected readonly PAGE_SIZE_OPTIONS = [5, 10, 20];

  // ── Pagination state ──────────────────────────────────────────────────────

  /** 0-based page index, as PrimeNG Paginator expects. */
  readonly first = signal(0);
  readonly pageSize = signal(10);

  /**
   * Derived 1-based page number sent to the API.
   * Kept as a plain getter to avoid an extra computed — rxResource
   * reads first() and pageSize() directly in its request factory.
   */

  // ── Accordion state ───────────────────────────────────────────────────────

  readonly openValues = signal<string[]>([]);

  // ── Skeleton rows matches current pageSize ────────────────────────────────

  readonly skeletonRows = computed(() =>
    Array.from({ length: this.pageSize() }),
  );

  // ── Resource ─────────────────────────────────────────────────────────────

  readonly panelsResource = rxResource({
    // Re-fetches automatically whenever first or pageSize change.
    request: () => ({
      page: this.first() / this.pageSize() + 1,
      pageSize: this.pageSize(),
    }),
    loader: ({ request }) => this.api.getPanels(request.page, request.pageSize),
  });

  // ── Events ───────────────────────────────────────────────────────────────

  onValueChange(newValues: string | number | string[] | number[]): void {
    this.openValues.set(newValues as string[]);
  }

  onPageChange(event: PaginatorState): void {
    this.first.set(event.first ?? 0);
    this.pageSize.set(event.rows ?? 10);
    // Collapse all panels — their content belongs to the previous page.
    this.openValues.set([]);
  }
}
