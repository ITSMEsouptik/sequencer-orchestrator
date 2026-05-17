import { OrderStatus } from "../enum/OrderStatus";

export interface Order {
    patientName: string;
    orderId: string;
    status: OrderStatus;
    updatedAt: Date;
    createdAt: Date;
}