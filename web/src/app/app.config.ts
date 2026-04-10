// app.config.ts
import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { providePrimeNG } from 'primeng/config';
import Aura from '@primeng/themes/aura'; // or Lara / Nora
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideHttpClient(),
    provideRouter(routes),
    provideAnimationsAsync(),
    providePrimeNG({
      theme: { preset: Aura },
      ripple: true,
    }),
    // Note: ConfirmationService and MessageService are provided inside
    // AccordionListComponent itself (providers: []) so that the p-toast
    // and p-confirmDialog declared in that template can serve all child
    // PanelContentComponent instances without a global singleton conflict.
  ],
};
