import { OrderStatus } from "../enum/OrderStatus";

export interface OrderStatusHistory {
    fromStatus: OrderStatus | null;
    toStatus: OrderStatus;
    changedAt: Date; 
}