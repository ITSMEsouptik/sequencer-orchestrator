import { Component, Inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatTableModule } from '@angular/material/table';
import { OrderStatusHistory } from '../../interfaces/OrderStatusHistory';

export interface OrderHistoryDialogData {
  orderId: string;
  history: OrderStatusHistory[];
}

@Component({
  selector: 'app-order-history-dialog',
  imports: [MatDialogModule, MatTableModule, MatButtonModule, DatePipe],
  template: `
    <h2 mat-dialog-title>Status History</h2>
    <p style="padding: 0 24px; color: grey; font-size: 12px;">{{ data.orderId }}</p>
    <mat-dialog-content>
      <table mat-table [dataSource]="data.history" class="mat-elevation-z2" style="width: 100%">
        <ng-container matColumnDef="fromStatus">
          <th mat-header-cell *matHeaderCellDef>From</th>
          <td mat-cell *matCellDef="let h">{{ h.fromStatus ?? '—' }}</td>
        </ng-container>
        <ng-container matColumnDef="toStatus">
          <th mat-header-cell *matHeaderCellDef>To</th>
          <td mat-cell *matCellDef="let h">{{ h.toStatus }}</td>
        </ng-container>
        <ng-container matColumnDef="changedAt">
          <th mat-header-cell *matHeaderCellDef>Changed At</th>
          <td mat-cell *matCellDef="let h">{{ h.changedAt | date:'medium' }}</td>
        </ng-container>
        <tr mat-header-row *matHeaderRowDef="columns"></tr>
        <tr mat-row *matRowDef="let row; columns: columns"></tr>
      </table>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Close</button>
    </mat-dialog-actions>
  `,
})
export class OrderHistoryDialogComponent {
  columns = ['fromStatus', 'toStatus', 'changedAt'];
  constructor(@Inject(MAT_DIALOG_DATA) public data: OrderHistoryDialogData) {}
}
