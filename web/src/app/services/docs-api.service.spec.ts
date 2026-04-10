import { TestBed } from '@angular/core/testing';

import { DocsApiService } from './docs-api.service';

describe('DocsApiService', () => {
  let service: DocsApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(DocsApiService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
