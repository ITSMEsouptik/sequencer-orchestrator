import { HttpClient } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { OrderStatus } from "../enum/OrderStatus";
import { Observable } from "rxjs";
import { Order } from "../interfaces/Order";
import { OrderStatusHistory } from "../interfaces/OrderStatusHistory";

@Injectable({ providedIn: 'root' })
export class OrderService {
    private http = inject(HttpClient);

    getOrders(status?: OrderStatus): Observable<Order[]> {
        const params = status != null ? { status: OrderStatus[status] } : undefined;
        return this.http.get<Order[]>('/api/orders', { params });
    }

    getStatusHistory(orderId: string) : Observable<OrderStatusHistory[]> {
        return this.http.get<OrderStatusHistory[]>(`/api/orders/${orderId}/history`);
    }
}