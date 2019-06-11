// Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React from "react";
import Button from 'react-bootstrap/Button'
import Spinner from 'react-bootstrap/Spinner'
import "./LoaderButton.css";

export default ({
  isLoading,
  text,
  loadingText,
  className = "",
  disabled = false,
  ...props
}) =>
  <Button
    className={`LoaderButton ${className}`}
    disabled={disabled || isLoading}
    {...props}
  >
    {isLoading && <Spinner animation="border" role="status"> <span className="sr-only">Loading...</span> </Spinner>}
    {!isLoading ? text : loadingText}
  </Button>;
