# Driver Verification System

The verification system ensures that every driver on the platform has valid documentation and meets safety standards before they can accept rides.

## The Document Approval Flow

1. **Upload**: Driver uploads photos of their **Driving License**, **RC**, and **Vehicle Insurance**.
2. **Pending State**: Documents enter the `PENDING` state and are visible on the Admin Dashboard.
3. **Review**: An Admin user reviews the images.
4. **Terminal State**:
- **APPROVED**: Document is verified.
- **REJECTED**: Driver is notified with a reason (e.g.,"Image too blurry") and must re-upload.

## Automated Verification Trigger

The system uses a subset-check logic to automatically activate driver accounts. 

### Required Document Set:
- `LICENSE`
- `RC` (Registration Certificate)
- `INSURANCE`

**Auto-Activation Logic:**
When an admin approves a document, the system checks the aggregate status of all the driver's documents. If the **Required Set** is fully satisfied (all three are `APPROVED`), the `Driver.is_verified` flag is set to `True`.

## Messaging & Notifications

- On **Approval**: Push notification:"Your [Document Type] has been approved."
- On **Rejection**: Push notification:"Your [Document Type] was rejected: [Reason]. Please re-upload."
- On **Full Verification**: Push notification:"Congratulations! Your profile has been verified. You can now go ONLINE."

## Future Enhancements

- **OCR Integration**: Proof-of-concept for automated text extraction from licenses to reduce manual admin workload.
- **Expiry Monitoring**: Automated alerts for drivers (and admins) 30 days before a document (Insurance/License) expires.
