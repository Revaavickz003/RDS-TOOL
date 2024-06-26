from django.contrib import messages
from django.shortcuts import redirect
from frontend.models import OrgType, Location, City, LeadTable, ProductTable, customertable, UserActivity
import pandas as pd
from django.utils import timezone
from django.http import HttpResponse
from openpyxl import Workbook
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required

@login_required(login_url='/login')
def customer_import_view(request):
    if request.method == 'POST':
        import_file = request.FILES.get('import_file')
        if import_file:
            if not import_file.name.endswith('.xlsx'):
                messages.error(request, "Only Excel files (.xlsx) are supported.")
                return redirect('coustomer')

            try:
                df = pd.read_excel(import_file)

                for index, row in df.iterrows():
                    try:
                        org_name = row.get('Company Name')

                        # Handle Business Type
                        business_type = row.get('Business type')
                        if not business_type:
                            messages.error(request, f"Error on row {index + 2}: Business Type is missing.")
                            continue
                        elif business_type not in dict(customertable.BUSINESS_TYPE_CHOICES).keys():
                            messages.error(request, f"Error on row {index + 2}: Invalid Business Type '{business_type}'.")
                            continue

                        # Get OrgType
                        try:
                            org_type = OrgType.objects.get(org_type=row.get('Company Type'))
                        except OrgType.DoesNotExist:
                            messages.error(request, f"Error on row {index + 2}: Company Type '{row.get('Company Type')}' does not exist.")
                            continue

                        # Get Location
                        try:
                            location = Location.objects.get(location=row.get('Country'))
                        except Location.DoesNotExist:
                            messages.error(request, f"Error on row {index + 2}: Country '{row.get('Country')}' does not exist.")
                            continue

                        # Get City
                        try:
                            city = City.objects.get(city=row.get('City'))
                        except City.DoesNotExist:
                            messages.error(request, f"Error on row {index + 2}: City '{row.get('City')}' does not exist.")
                            continue

                        # Get Lead Name
                        try:
                            lead_name = LeadTable.objects.get(Lead_Name=row.get('Refarrel Name'))
                        except LeadTable.DoesNotExist:
                            messages.error(request, f"Error on row {index + 2}: Referral Name '{row.get('Refarrel Name')}' does not exist.")
                            continue

                        # Handle products
                        product_names = [p.strip() for p in str(row.get('Products')).split(',')]
                        if not product_names:
                            messages.warning(request, f"No products specified for company '{org_name}'.")
                            continue
                        
                        selected_products = []
                        for product_name in product_names:
                            try:
                                product = ProductTable.objects.get(Product_Name=product_name)
                                selected_products.append(product)
                            except ProductTable.DoesNotExist:
                                messages.error(request, f"Error on row {index + 2}: Product '{product_name}' does not exist.")
                                continue

                        # Handle end_of_date
                        end_of_date = row.get('End of Date')
                        if pd.isnull(end_of_date):
                            end_of_date = timezone.now().date()

                        # Handle follow_up
                        follow_up_date_str = row.get('Follow up')
                        if pd.isnull(follow_up_date_str):
                            follow_up_date_str = timezone.now().date()

                        # Handle Company Name
                        if not org_name:
                            messages.error(request, f"Error on row {index + 2}: Company Name is missing.")
                            continue

                        existing_org = customertable.objects.filter(org_name=org_name).first()
                        if existing_org:
                            messages.error(request, f"Error on row {index + 2}: Company '{org_name}' already exists.")
                            continue

                        new_customer = customertable.objects.create(
                            client_name=row.get('Client Name', ''),
                            client_number=row.get('Client Number', ''),
                            org_name=org_name,
                            org_type=org_type,
                            location=location,
                            city=city,
                            lead_name=lead_name,
                            business_type=business_type,
                            amount=int(row.get('Budget', 0)),
                            end_of_date=end_of_date,
                            priority=row.get('Priority', ''),
                            mail_id=row.get('Email', ''),
                            status=row.get('Status', ''),
                            comment=row.get('Additional Remarks', ''),
                            remarks=row.get('Call Back Comments', ''),
                            follow_up=follow_up_date_str,
                            created_by=request.user,
                            updated_by=request.user,
                        )
                        new_customer.products.set(selected_products)
                        
                        # Create a new lead history entry
                        UserActivity.objects.create(
                            user=request.user,
                            timestamp=timezone.now(),
                            lable=f"{new_customer.org_name}",
                            action="Upload customers sheet",
                            content_type=ContentType.objects.get_for_model(customertable),
                            object_id=new_customer.pk,
                        )

                    except Exception as e:
                        messages.error(request, f"Error creating customer on row {index + 2}: {str(e)}")
                        continue

                return redirect('coustomer')  # Redirect to appropriate URL

            except Exception as e:
                messages.error(request, f"Error reading Excel file: {str(e)}")
                return redirect('coustomer')  # Redirect to appropriate URL

        else:
            messages.error(request, "No file uploaded.")
            return redirect('coustomer')  # Redirect to appropriate URL

    return redirect('coustomer')  # Redirect to appropriate URL

# Export data

@login_required(login_url='/login')
def export_customer_data(request):
    # Query all coustomer
    Customers = customertable.objects.all()

    # Create a new workbook and select the active worksheet
    wb = Workbook()
    ws = wb.active

    # Define column headers
    headers = [
        'Client Id',
        'Client Name', 
        'Client Number', 
        'Company Name', 
        'Company Type',
        'Location', 
        'City', 
        'Business Type',
        'Products',
        'Amount',
        'Created Date',
        'End of Date',
        'Lead Name', 
        'Priority',
        'Mail ID', 
        'Status', 
        'Comment', 
        'Remarks', 
        'Follow Up', 
        'Created By', 
        'Updated By', 
        'Updated Date'
    ]
    ws.append(headers)

    # Append lead data to worksheet
    for Customer in Customers:
        product_names = ", ".join([product.Product_Name for product in Customer.products.all()])
        Customer_data = [
            Customer.customer_id,
            Customer.client_name, 
            Customer.client_number, 
            Customer.org_name, 
            Customer.org_type.org_type,
            Customer.location.location, 
            Customer.city.city, 
            Customer.business_type,
            product_names,  # Modify this line to include product names as a comma-separated string
            Customer.amount,
            Customer.created_date,
            Customer.end_of_date,
            Customer.lead_name.Lead_Name,
            Customer.priority, 
            Customer.mail_id, 
            Customer.status,
            Customer.comment, 
            Customer.remarks, 
            Customer.follow_up, 
            Customer.created_by.username, 
            Customer.updated_by.username, 
            Customer.updated_date
        ]
        ws.append(Customer_data)

    # Save the workbook to a file
    filename = 'Customers_export.xlsx'
    wb.save(filename)

    # Serve the XLSX file as a download response
    with open(filename, 'rb') as file:
        response = HttpResponse(file.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=' + filename
        return response