import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AccordionListComponent } from './accordion-list.component';

describe('AccordionListComponent', () => {
  let component: AccordionListComponent;
  let fixture: ComponentFixture<AccordionListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccordionListComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AccordionListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
