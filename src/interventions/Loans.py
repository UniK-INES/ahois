"""
Provides a class to model and calculate loan conditions for financing.

This module contains the `Loan` class, which is used to determine the terms of
a loan for purchasing a heating system. 

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
"""
import math
import logging

logger = logging.getLogger("waermer.intervention.loan")

class Loan:
    """
    Represents a loan for purchasing a heating system.
    This class encapsulates the logic for determining the terms of a loan.
    When an instance is created, it automatically calculates the loan amount,
    which is the lesser of the required amount (system price minus available
    funds) and the maximum affordable amount (based on income). It then
    computes the total repayment and monthly payment based on the loan term
    and interest rate using standard financial formulas.

    Parameters
    ----------
    weekly_income : float
        The borrower's weekly net income in EUR.
    system_price : float
        The total price of the heating system in EUR.
    funds : float
        The amount of personal funds the borrower has available to put towards
        the purchase.
    interest : float, optional
        The annual interest rate as a decimal (e.g., 0.0221 for 2.21%), by
        default 0.0221.
    years : int, optional
        The loan term in years, by default 10.

    Attributes
    ----------
    interest : float
        The annual interest rate.
    years : int
        The loan term in years.
    loan_amount : float
        The calculated principal amount of the loan in EUR.
    total_repayment : float
        The total amount that will be paid back over the life of the loan.
    monthly_payment : float
        The calculated monthly payment amount in EUR.
    """
    def __init__(self, weekly_income, system_price, funds, interest=0.0221, years=10):
        """
        Initialises a Loan instance and calculates its terms.

        The constructor determines the affordable loan amount based on income,
        calculates the required loan (price minus funds), and takes the
        minimum of the two as the principal. It then computes the total and
        monthly repayments.

        Parameters
        ----------
        weekly_income : float
            The borrower's weekly net income in EUR.
        system_price : float
            The total price of the heating system in EUR.
        funds : float
            The amount of personal funds the borrower has available.
        interest : float, optional
            The annual interest rate, by default 0.0221.
        years : int, optional
            The loan term in years, by default 10.
        """
        self.interest = interest  # Annual interest rate
        self.years = years  # Loan term in years
        
        # Step 1: Convert weekly net income to annual net income
        monthly_net_income = weekly_income * 4

        # Step 2: Calculate the maximum affordable loan amount based on LTI ratio (LTV 100%)
        ltv_ratio = 1 #Maximum possible loan share from the price
        lti_multiplier = 5 #Yearly income x lti
        affordable_loan_amount = min((ltv_ratio*system_price), (monthly_net_income * 12 * lti_multiplier))

        # Step 3: Calculate the required loan amount
        required_loan_amount = max(0, system_price - funds)

        # Step 4: Use the required loan amount if it's within the affordable limit; otherwise, use the maximum affordable amount
        self.loan_amount = math.ceil(min(required_loan_amount, affordable_loan_amount))

        # Step 5: Calculate the monthly interest rate and total number of payments
        monthly_interest = interest / 12
        total_payments = years * 12

        # Step 6: Calculate the total repayment amount with monthly compound interest
        self.total_repayment = math.floor(self.loan_amount * ((1 + monthly_interest) ** total_payments))

        # Step 7: Calculate monthly payment using the amortization formula
        payment = math.ceil(self.loan_amount * (monthly_interest * (1 + monthly_interest) ** total_payments) / ((1 + monthly_interest) ** total_payments - 1))
        self.monthly_payment = math.floor(payment)
        if self.monthly_payment < 0:
            raise Exception("Negative monthly payment!")
    
    def log_details(self):
        logger.info(f"Required loan amount: {self.required_loan_amount}")
        logger.info(f"Monthly net income: {self.monthly_net_income}")
        logger.info(f"Affordable loan amount: {self.affordable_loan_amount}")
        logger.info(f"Loan amount: {self.loan_amount}")
        logger.info(f"System costs: {self.system_price}")
        logger.info(f"Funds: {self.funds}")
