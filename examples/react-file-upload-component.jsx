import React, { useState } from "react";

/**
 * Complete example: Product form with file uploads
 * Demonstrates how to create documents with file uploads using CocoBase
 */

const ProductFormWithFiles = () => {
  const [formData, setFormData] = useState({
    name: "",
    price: "",
    description: "",
    category: "electronics",
  });

  const [selectedFiles, setSelectedFiles] = useState([]);
  const [previewUrls, setPreviewUrls] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const API_KEY = process.env.REACT_APP_COCOBASE_API_KEY;
  const BASE_URL = "https://api.cocobase.com";

  // Handle text input changes
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  // Handle file selection
  const handleFileChange = (e) => {
    const files = Array.from(e.target.files);
    setSelectedFiles(files);

    // Create preview URLs
    const previews = files.map((file) => URL.createObjectURL(file));
    setPreviewUrls(previews);
  };

  // Remove a selected file
  const removeFile = (index) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    setPreviewUrls((prev) => prev.filter((_, i) => i !== index));
  };

  // Create product with files
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      // Create FormData
      const data = new FormData();

      // Add product data as JSON string
      data.append(
        "data",
        JSON.stringify({
          name: formData.name,
          price: parseFloat(formData.price),
          description: formData.description,
          category: formData.category,
        })
      );

      // Add all selected files
      selectedFiles.forEach((file) => {
        data.append("files", file);
      });

      // Send request
      const response = await fetch(
        `${BASE_URL}/collections/documents?collection=products`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${API_KEY}`,
          },
          body: data,
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to create product");
      }

      const result = await response.json();

      setSuccess("Product created successfully!");
      console.log("Created product:", result);

      // Show file URLs
      if (result.data.file_url) {
        console.log("File URL:", result.data.file_url);
      } else if (result.data.file_urls) {
        console.log("File URLs:", result.data.file_urls);
      }

      // Reset form
      setFormData({
        name: "",
        price: "",
        description: "",
        category: "electronics",
      });
      setSelectedFiles([]);
      setPreviewUrls([]);
    } catch (err) {
      setError(err.message);
      console.error("Error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6">Create Product with Images</h2>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
          {success}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Product Name */}
        <div>
          <label className="block text-sm font-medium mb-2">
            Product Name *
          </label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleInputChange}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Gaming Laptop"
          />
        </div>

        {/* Price */}
        <div>
          <label className="block text-sm font-medium mb-2">Price ($) *</label>
          <input
            type="number"
            name="price"
            value={formData.price}
            onChange={handleInputChange}
            required
            step="0.01"
            min="0"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="99.99"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium mb-2">Description</label>
          <textarea
            name="description"
            value={formData.description}
            onChange={handleInputChange}
            rows="4"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Product description..."
          />
        </div>

        {/* Category */}
        <div>
          <label className="block text-sm font-medium mb-2">Category</label>
          <select
            name="category"
            value={formData.category}
            onChange={handleInputChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="electronics">Electronics</option>
            <option value="clothing">Clothing</option>
            <option value="books">Books</option>
            <option value="home">Home & Garden</option>
          </select>
        </div>

        {/* File Upload */}
        <div>
          <label className="block text-sm font-medium mb-2">
            Product Images
          </label>
          <input
            type="file"
            onChange={handleFileChange}
            multiple
            accept="image/*"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-sm text-gray-500 mt-1">
            Select one or more images (jpg, png, gif)
          </p>
        </div>

        {/* Image Previews */}
        {previewUrls.length > 0 && (
          <div>
            <label className="block text-sm font-medium mb-2">
              Selected Images ({selectedFiles.length})
            </label>
            <div className="grid grid-cols-3 gap-4">
              {previewUrls.map((url, index) => (
                <div key={index} className="relative">
                  <img
                    src={url}
                    alt={`Preview ${index + 1}`}
                    className="w-full h-32 object-cover rounded-lg"
                  />
                  <button
                    type="button"
                    onClick={() => removeFile(index)}
                    className="absolute top-1 right-1 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center hover:bg-red-600"
                  >
                    ×
                  </button>
                  <p className="text-xs text-gray-600 mt-1 truncate">
                    {selectedFiles[index].name}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading}
          className={`w-full py-3 px-4 rounded-lg text-white font-medium ${
            loading
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-blue-500 hover:bg-blue-600"
          }`}
        >
          {loading ? "Creating Product..." : "Create Product"}
        </button>
      </form>
    </div>
  );
};

export default ProductFormWithFiles;

/**
 * EXAMPLE 2: Update Product with New Images
 */

export const UpdateProductWithFiles = ({ productId, initialData }) => {
  const [formData, setFormData] = useState(initialData);
  const [newFiles, setNewFiles] = useState([]);
  const [loading, setLoading] = useState(false);

  const API_KEY = process.env.REACT_APP_COCOBASE_API_KEY;
  const BASE_URL = "https://api.cocobase.com";

  const handleUpdate = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const data = new FormData();

      // Add updated data
      data.append(
        "data",
        JSON.stringify({
          name: formData.name,
          price: formData.price,
          description: formData.description,
        })
      );

      // Add new files (will be appended to existing file_urls)
      newFiles.forEach((file) => {
        data.append("files", file);
      });

      const response = await fetch(
        `${BASE_URL}/collections/products/documents/${productId}`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${API_KEY}`,
          },
          body: data,
        }
      );

      if (!response.ok) {
        throw new Error("Failed to update product");
      }

      const result = await response.json();
      console.log("Updated product:", result);

      alert("Product updated successfully!");
    } catch (err) {
      console.error("Error:", err);
      alert("Failed to update product");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleUpdate}>
      {/* Form fields similar to create form */}

      <input
        type="file"
        multiple
        onChange={(e) => setNewFiles(Array.from(e.target.files))}
      />

      <button type="submit" disabled={loading}>
        {loading ? "Updating..." : "Update Product"}
      </button>
    </form>
  );
};

/**
 * EXAMPLE 3: Simple File Upload Hook
 */

export const useFileUpload = () => {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  const createDocumentWithFiles = async (collection, data, files) => {
    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("data", JSON.stringify(data));

      files.forEach((file) => {
        formData.append("files", file);
      });

      const response = await fetch(
        `${process.env.REACT_APP_API_URL}/collections/documents?collection=${collection}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${process.env.REACT_APP_API_KEY}`,
          },
          body: formData,
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Upload failed");
      }

      return await response.json();
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setUploading(false);
    }
  };

  return { createDocumentWithFiles, uploading, error };
};

// Usage:
// const { createDocumentWithFiles, uploading } = useFileUpload();
// const result = await createDocumentWithFiles('products', { name: 'Product' }, files);
