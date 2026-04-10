import React, { useState } from 'react'
import { uploadBill } from '../api'
import '../styles/BillUploadPanel.css'

export default function BillUploadPanel({ onBillProcessed }) {
  const [bill, setBill] = useState({
    bill_id: '',
    customer_id: '',
    customer_name: '',
    timestamp: new Date().toISOString().split('T')[0] + 'T' + new Date().toTimeString().slice(0, 5),
    items: [{ product_id: '', name: '', quantity: '', price: '' }],
  })

  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const fileInputRef = React.useRef(null)

  const handleBillChange = (field, value) => {
    setBill(prev => ({ ...prev, [field]: value }))
    setError(null)
  }

  const handleItemChange = (index, field, value) => {
    const newItems = [...bill.items]
    newItems[index] = { ...newItems[index], [field]: value }
    setBill(prev => ({ ...prev, items: newItems }))
  }

  const addItem = () => {
    setBill(prev => ({
      ...prev,
      items: [...prev.items, { product_id: '', name: '', quantity: '', price: '' }],
    }))
  }

  const removeItem = (index) => {
    if (bill.items.length > 1) {
      setBill(prev => ({
        ...prev,
        items: prev.items.filter((_, i) => i !== index),
      }))
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      // Validate required fields
      if (!bill.bill_id.trim()) throw new Error('Bill ID is required')
      if (!bill.customer_id.trim()) throw new Error('Customer ID is required')
      if (!bill.customer_name.trim()) throw new Error('Customer Name is required')
      if (bill.items.length === 0) throw new Error('At least one item is required')

      // Validate items
      bill.items.forEach((item, idx) => {
        if (!item.product_id.trim()) throw new Error(`Item ${idx + 1}: Product ID is required`)
        if (!item.name.trim()) throw new Error(`Item ${idx + 1}: Product Name is required`)
        if (!item.quantity || parseFloat(item.quantity) <= 0) {
          throw new Error(`Item ${idx + 1}: Quantity must be positive`)
        }
        if (!item.price || parseFloat(item.price) <= 0) {
          throw new Error(`Item ${idx + 1}: Price must be positive`)
        }
      })

      // Convert quantities and prices to numbers
      const billData = {
        ...bill,
        items: bill.items.map(item => ({
          ...item,
          quantity: parseFloat(item.quantity),
          price: parseFloat(item.price),
        })),
      }

      const response = await uploadBill(billData)

      setResult(response)
      
      // Handle error response
      if (!response.success) {
        throw new Error(response.error || response.message || 'Bill processing failed')
      }
      
      // Reset form on success
      if (response.success) {
        setBill({
          bill_id: '',
          customer_id: '',
          customer_name: '',
          timestamp: new Date().toISOString().split('T')[0] + 'T' + new Date().toTimeString().slice(0, 5),
          items: [{ product_id: '', name: '', quantity: '', price: '' }],
        })
        
        // Call callback to refresh other panels
        if (onBillProcessed) {
          onBillProcessed(response)
        }
      }
    } catch (err) {
      console.error('Bill upload error:', err)
      setError(err.message || 'Failed to process bill')
    } finally {
      setLoading(false)
    }
  }

  const handleLoadSample = () => {
    setBill({
      bill_id: `B${Math.floor(Math.random() * 10000)}`,
      customer_id: `C${Math.floor(Math.random() * 1000)}`,
      customer_name: 'Sample Customer',
      timestamp: new Date().toISOString().slice(0, 16),
      items: [
        { product_id: 'P001', name: 'atta', quantity: '2', price: '500' },
        { product_id: 'P002', name: 'chawal', quantity: '1', price: '600' },
      ],
    })
    setError(null)
    setResult(null)
  }

  const handleImportBill = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    setError(null)
    setResult(null)

    try {
      const fileContent = await file.text()
      let importedBill = null

      if (file.name.endsWith('.json')) {
        importedBill = JSON.parse(fileContent)
      } else if (file.name.endsWith('.csv')) {
        importedBill = parseCSVBill(fileContent)
      } else {
        throw new Error('Unsupported file format. Use JSON or CSV.')
      }

      // Validate imported data
      if (!importedBill.bill_id || !importedBill.customer_id || !importedBill.items) {
        throw new Error('Invalid bill format. Missing required fields.')
      }

      // Ensure items is an array
      if (!Array.isArray(importedBill.items)) {
        throw new Error('Items must be an array')
      }

      // Convert items to string format for form
      const formattedItems = importedBill.items.map(item => ({
        product_id: String(item.product_id || ''),
        name: String(item.name || ''),
        quantity: String(item.quantity || ''),
        price: String(item.price || ''),
      }))

      setBill({
        bill_id: String(importedBill.bill_id || ''),
        customer_id: String(importedBill.customer_id || ''),
        customer_name: String(importedBill.customer_name || ''),
        timestamp: importedBill.timestamp || new Date().toISOString().slice(0, 19),
        items: formattedItems,
      })

      setResult({
        success: true,
        message: `✅ Bill imported successfully from ${file.name}`,
      })
    } catch (err) {
      setError(err.message || 'Failed to import bill')
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const parseCSVBill = (csvContent) => {
    const lines = csvContent.trim().split('\n')
    const bill = {
      bill_id: '',
      customer_id: '',
      customer_name: '',
      timestamp: '',
      items: [],
    }

    let inItemsSection = false

    for (const line of lines) {
      if (line.includes('Items') || line.includes('Product ID')) {
        inItemsSection = true
        continue
      }

      if (inItemsSection) {
        if (line.trim() === '' || line.includes('Product ID')) continue

        const parts = line.split(',').map(p => p.trim())
        if (parts.length >= 4 && parts[0] !== 'Product ID') {
          bill.items.push({
            product_id: parts[0],
            name: parts[1],
            quantity: parseFloat(parts[2]) || 0,
            price: parseFloat(parts[3]) || 0,
          })
        }
      } else {
        const [key, value] = line.split(',').map(p => p.trim())
        if (key === 'Bill ID') bill.bill_id = value
        else if (key === 'Customer ID') bill.customer_id = value
        else if (key === 'Customer Name') bill.customer_name = value
        else if (key === 'Timestamp') bill.timestamp = value
      }
    }

    return bill
  }

  return (
    <div className="bill-upload-panel">
      <h2>📋 Upload Bill</h2>
      
      <div className="bill-upload-container">
        <form onSubmit={handleSubmit} className="bill-form">
          {/* Bill Header Info */}
          <div className="form-section">
            <h3>Bill Information</h3>
            <div className="form-row">
              <div className="form-group">
                <label>Bill ID</label>
                <input
                  type="text"
                  value={bill.bill_id}
                  onChange={(e) => handleBillChange('bill_id', e.target.value)}
                  placeholder="e.g., B1002"
                  disabled={loading}
                />
              </div>
              <div className="form-group">
                <label>Customer ID</label>
                <input
                  type="text"
                  value={bill.customer_id}
                  onChange={(e) => handleBillChange('customer_id', e.target.value)}
                  placeholder="e.g., C001"
                  disabled={loading}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Customer Name</label>
                <input
                  type="text"
                  value={bill.customer_name}
                  onChange={(e) => handleBillChange('customer_name', e.target.value)}
                  placeholder="e.g., Rahul"
                  disabled={loading}
                />
              </div>
              <div className="form-group">
                <label>Date & Time</label>
                <input
                  type="datetime-local"
                  value={bill.timestamp}
                  onChange={(e) => handleBillChange('timestamp', e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>
          </div>

          {/* Items Section */}
          <div className="form-section">
            <h3>Items</h3>
            <div className="items-list">
              {bill.items.map((item, index) => (
                <div key={index} className="item-row">
                  <input
                    type="text"
                    value={item.product_id}
                    onChange={(e) => handleItemChange(index, 'product_id', e.target.value)}
                    placeholder="Product ID"
                    disabled={loading}
                  />
                  <input
                    type="text"
                    value={item.name}
                    onChange={(e) => handleItemChange(index, 'name', e.target.value)}
                    placeholder="Product Name"
                    disabled={loading}
                  />
                  <input
                    type="number"
                    value={item.quantity}
                    onChange={(e) => handleItemChange(index, 'quantity', e.target.value)}
                    placeholder="Qty"
                    step="0.01"
                    disabled={loading}
                  />
                  <input
                    type="number"
                    value={item.price}
                    onChange={(e) => handleItemChange(index, 'price', e.target.value)}
                    placeholder="Price"
                    step="0.01"
                    disabled={loading}
                  />
                  {bill.items.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeItem(index)}
                      className="btn-remove"
                      disabled={loading}
                    >
                      ✕
                    </button>
                  )}
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={addItem}
              className="btn-add-item"
              disabled={loading}
            >
              + Add Item
            </button>
          </div>

          {/* Error Display */}
          {error && (
            <div className="error-message">
              ❌ {error}
            </div>
          )}

          {/* Result Display */}
          {result && (
            <div className={`result-message ${result.success ? 'success' : 'failure'}`}>
              {result.message}
              {result.success && (
                <div className="result-details">
                  <p>✅ Items Processed: {result.items_processed}</p>
                  <p>✅ Sales Recorded: {result.sales_records_created}</p>
                  <p>{result.inventory_updated ? '✅' : '❌'} Inventory Updated</p>
                  <p>{result.trends_refreshed ? '✅' : '❌'} Trends Refreshed</p>
                </div>
              )}
              {result.error && (
                <p className="error-detail">Error: {result.error}</p>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="form-actions">
            <button
              type="submit"
              className="btn-submit"
              disabled={loading}
            >
              {loading ? '⏳ Processing...' : '✅ Upload Bill'}
            </button>
            <button
              type="button"
              onClick={handleLoadSample}
              className="btn-sample"
              disabled={loading}
            >
              📝 Load Sample
            </button>
            <label className="btn-import" htmlFor="bill-file-input">
              📥 Import Bill
            </label>
            <input
              ref={fileInputRef}
              id="bill-file-input"
              type="file"
              accept=".json,.csv"
              onChange={handleImportBill}
              style={{ display: 'none' }}
              disabled={loading}
            />
          </div>
        </form>
      </div>
    </div>
  )
}
