import { Component, computed, signal, OnDestroy, OnInit } from '@angular/core';
import { Order } from '../../interfaces/Order';
import { OrderStatus } from '../../enum/OrderStatus';
import { OrderService } from '../../services/order.service';
import { interval, Subscription, switchMap, startWith } from 'rxjs';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog } from '@angular/material/dialog';
import { OrderHistoryDialogComponent } from './order-history-dialog';
@Component({
  selector: 'app-dashboard',
  imports: [MatTableModule, MatChipsModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class Dashboard implements OnInit, OnDestroy {

  private subscription!: Subscription
  constructor(
    private orderService: OrderService,
    private dialog: MatDialog,
  ) {}

  ngOnInit(): void {
    this.subscription = interval(5000).pipe(
      startWith(0),
      switchMap(() => this.orderService.getOrders())
    ).subscribe(orders => this.orders.set(orders))
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }

  orders = signal<Order[]>([]);

  activeOrders = computed(() => this.orders().
    filter(order => {
      const excludedStatuses = [OrderStatus.CLOSED, OrderStatus.FAILED, OrderStatus.CANCELLED];
      return !excludedStatuses.includes(order.status);
    }).length);
  
  displayedColumns = ['orderId', 'patientName', 'status', 'daysSinceCreation', 'lastUpdated'];
  
  daysSinceCreation(createdAt: Date): number {
    const now = new Date();
    const createdDate = new Date(createdAt);
    const diffTime = Math.abs(now.getTime() - createdDate.getTime());
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  }

  timeSinceUpdate(updatedAt: Date): string {
    const now = new Date();
    const updatedDate = new Date(updatedAt);
    const diffTime = Math.abs(now.getTime() - updatedDate.getTime());
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor((diffTime / (1000 * 60 * 60)) % 24);
    const diffMinutes = Math.floor((diffTime / (1000 * 60)) % 60);

    if (diffDays > 0) {
      return `${diffDays} day(s) ago`;
    } else if (diffHours > 0) {
      return `${diffHours} hour(s) ago`;
    } else if (diffMinutes > 0) {
      return `${diffMinutes} minute(s) ago`;
    } else {
      return 'Just now';
    }
  }

  statusColor(status: OrderStatus) : string {
    const colorMap = {
      "CLOSED": 'green',
      "FAILED": 'red',
      "MANUFACTURING" : 'blue'
    }
    
    const color = colorMap[OrderStatus[status] as keyof typeof colorMap] || 'yellow';
    return color;
  }

  onRowClick(order: Order): void {
    this.orderService.getStatusHistory(order.orderId).subscribe(history => {
      this.dialog.open(OrderHistoryDialogComponent, {
        width: '600px',
        data: { orderId: order.orderId, history },
      });
    });
  }
}
