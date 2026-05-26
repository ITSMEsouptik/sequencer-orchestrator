import { Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { Order } from "../interfaces/Order";

@Injectable({providedIn: 'root'})
export class OrderStreamService {

    stream(): Observable<Order> {
        return new Observable(observer => {
            const eventSource = new EventSource('api/orders/stream');

            eventSource.onmessage = event => {
                observer.next(JSON.parse(event.data));
            };

            // Let EventSource handle reconnection natively — closing it here
            // would disable the browser's built-in retry and kill the stream permanently.
            eventSource.onerror = () => {};

            return () => eventSource.close();
        })
    }
}