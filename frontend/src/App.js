// Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React, { Component, Fragment } from "react";
import { withRouter } from "react-router-dom";
import "./App.css";
import Routes from "./Routes";
import { Auth } from "aws-amplify";
import Navbar from 'react-bootstrap/Navbar';
import Nav from 'react-bootstrap/Nav'
import Button from 'react-bootstrap/Button'


class App extends Component {
    constructor(props) {
  super(props);

  this.state = {
  isAuthenticated: false,
  isAuthenticating: true
};

}

async componentDidMount() {
  try {
    if (await Auth.currentSession()) {
      this.userHasAuthenticated(true);
    }
  }
  catch(e) {
    if (e !== 'No current user') {
      alert(e);
    }
  }

  this.setState({ isAuthenticating: false });
}


userHasAuthenticated = authenticated => {
  this.setState({ isAuthenticated: authenticated });
}

handleLogout = async event => {
  await Auth.signOut();

  this.userHasAuthenticated(false);

  this.props.history.push("/login");

}



  render() {
        const childProps = {
  isAuthenticated: this.state.isAuthenticated,
  userHasAuthenticated: this.userHasAuthenticated
};

    return (
        !this.state.isAuthenticating &&
      <div className="App container">
        <Navbar collapseOnSelect className="navbar navbar-expand-sm bg-dark navbar-dark">
          <Navbar.Brand><img
              src="/favicon-32x32.png"
              width="30"
              height="30"
              className="d-inline-block align-top"
              alt="Wafer Maps"
            />    Wafer Maps</Navbar.Brand>
          <Navbar.Toggle />
          <Navbar.Collapse>
            <Nav className="ml-auto mr-1">
              {this.state.isAuthenticated
              ? <Nav.Item onClick={this.handleLogout}><Button>Logout</Button></Nav.Item>
              : <Fragment>
                    <Nav.Item><Button href="/login">Login</Button></Nav.Item>
                </Fragment>
}
            </Nav>
          </Navbar.Collapse>
        </Navbar>
          <Routes childProps={childProps} />
      </div>
    );
  }
}

export default withRouter(App);

