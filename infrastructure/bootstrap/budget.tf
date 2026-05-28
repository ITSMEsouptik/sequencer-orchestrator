resource "aws_budgets_budget" "monthly_spend" {
  name         = "sequencer-monthly-budget"
  budget_type  = "COST"
  limit_amount = "30"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = ["mandalsouptik1998@gmail.com"]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = ["mandalsouptik1998@gmail.com"]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "FORECASTED"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = ["mandalsouptik1998@gmail.com"]
  }

}

output "budget_name" {
  value       = aws_budgets_budget.monthly_spend.name
  description = "Name of the monthly spend budget alarm"
}
