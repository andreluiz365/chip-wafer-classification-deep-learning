// Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React, { Component } from "react";
import "./Home.css";
import { API } from "aws-amplify";
import DropdownButton from 'react-bootstrap/DropdownButton';
import Dropdown from 'react-bootstrap/Dropdown';
import ButtonToolbar from 'react-bootstrap/ButtonToolbar';
import Button from 'react-bootstrap/Button'
import Container from 'react-bootstrap/Container';
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import Card from 'react-bootstrap/Card';
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import config from "../config";
import { toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

const unique = (value, index, self) => {
  return self.indexOf(value) === index;
}

export default class Home extends Component {
  constructor(props) {
    super(props);

    this.state = {
      isLoading: true,
      fabs: [],
      cameras: {},
      from_date: new Date(),
      to_date: new Date(),
      selectedFab: "",
      selectedCam: "",
      imglist: [],
      selectedImg: 0,
      accuracy: 0.0,
      selectedActual: ""
    };

    this.handleFromDate = this.handleFromDate.bind(this);
    this.handleToDate = this.handleToDate.bind(this);
    this.handleImgPrev = this.handleImgPrev.bind(this);
    this.handleImgNext = this.handleImgNext.bind(this);
    this.handleActualSelect = this.handleActualSelect.bind(this);
    this.handleActualSubmit = this.handleActualSubmit.bind(this);
  }

  async componentDidMount() {
  if (!this.props.isAuthenticated) {
    return;
  }

  try {
    const fabMap = await this.fabs();
    var d = new Date();
    d.setDate(d.getDate()-1);
    this.setState({ fabs: Object.keys(fabMap).filter(unique), cameras: fabMap, from_date: d});
  } catch (e) {
    console.log(e);
  }

  this.setState({ isLoading: false });
}


fabs() {
  console.log("Getting fabs");
  return API.get("fabs", "/devices");
}

getimages(fab, camera, from_date, to_date) {
  console.log("Getting images for fab " + fab + " and camera " + camera + " between " + from_date + " and " + to_date);
  if(camera !== "") {
    const fromts = from_date.getTime() / 1000.0;
    const tots = to_date.getTime() / 1000.0;

    return API.get("fabs", "/images?fab=" + fab + "&camera=" + camera + "&fromts=" + fromts + "&tots=" + tots);

  }
  else {
    return [];
  }
}

renderFabList(fabs) {
  return fabs.map(
    (fab) =>
          <Dropdown.Item eventKey={fab} key={fab} onSelect={this.handleFabSelect}>{fab}</Dropdown.Item>
  );
}

handleFabSelect= (eventKey, event) => {
  this.setState({ selectedFab: eventKey, selectedCam: "", imglist: [], selectedImg: 0, accuracy: 0.0, selectedActual: ""});
  console.log("Selected " + eventKey);
  console.log("Camera list: " + this.state.cameras[eventKey])
}

renderCameraList(selectedFab) {
  if(selectedFab !== "") {
    const camlist = this.state.cameras[selectedFab];
    return camlist.map(
      (cam) =>
            <Dropdown.Item eventKey={cam} key={cam} onSelect={this.handleCamSelect}>{cam}</Dropdown.Item>
    );
  }
}

async updateImgList(fab, camera, from_date, to_date) {
  const imglist = await this.getimages(fab, camera, from_date, to_date);
  var accuracy = 0.0;
  for(var ii = 0; ii < imglist.length; ii++) {
    const imgobj = imglist[ii];
    const imgpred = imgobj.prediction;
    if(imgpred !== 'none') {
      accuracy = accuracy + 1.0;
    }  
  }
  accuracy = accuracy / imglist.length * 100.0;
  this.setState({ imglist: imglist, accuracy: accuracy});
}
handleCamSelect= (eventKey, event) => {
  console.log("Selected " + eventKey);
  this.setState({ selectedCam: eventKey});
  this.updateImgList(this.state.selectedFab, eventKey, this.state.from_date, this.state.to_date);
}
handleActualSelect= (eventKey, event) => {
  console.log("Selected " + eventKey);
  this.setState({ selectedActual: eventKey })
}
handleActualSubmit= async () => {
  console.log("Submitting corrected classification: " + this.state.selectedActual);
  try {
    await API.post("fabs", "/groundtruth", {
      body: {
        'imgid': this.state.imglist[this.state.selectedImg].imgid,
        'fab': this.state.selectedFab,
        'camera': this.state.selectedCam,
        'truth': this.state.selectedActual
      }
    });
    toast("Feedback saved");
  }
  catch(e) {

  }
}

  renderLander() {
    return (
      <div className="lander">
        <h1>Chip Wafer Review</h1>
      </div>
    );
  }

  handleFromDate(date) {
    console.log("Selected " + date);
    this.setState({ from_date: date });
    this.updateImgList(this.state.selectedFab, this.state.selectedCam, date, this.state.to_date);
  }
  handleToDate(date) {
    console.log("Selected " + date);
    this.setState({ to_date: date });
    this.updateImgList(this.state.selectedFab, this.state.selectedCam, this.state.from_date, date);
  }
  handleImgPrev() {
    const curidx = this.state.selectedImg;
    const maxidx = this.state.imglist.length - 1;
    var nextidx = curidx - 1;
    if(nextidx < 0) {
      console.log("going back to max");
      nextidx = maxidx;
    }
    else {
      console.log("decrementing");
    }
    this.setState({ selectedImg: nextidx});
  }
  handleImgNext() {
    const curidx = this.state.selectedImg;
    const maxidx = this.state.imglist.length - 1;
    var nextidx = curidx + 1;
    if(nextidx > maxidx) {
      console.log("going back to 0");
      nextidx = 0;
    }
    else {
      console.log("incrementing");
    }
    this.setState({ selectedImg: nextidx});
  }

  renderImgCard(imglist, imgidx, fab, camera) {
    if(imglist.length > 0) {
      const imgobj = imglist[imgidx];
      const imgurl = "https://s3-" + 
        config.cognito.REGION + ".amazonaws.com/" + 
        config.images.bucket + "/" + 
        fab + "/" + 
        camera + "/" + 
        imgobj.imgid + ".png";
      console.log("Image URL: " + imgurl);
      return(
        <Card border="primary" className="text-center">
          <Card.Img variant="top" src={imgurl} />
          <Card.Body>
          <Button variant="outline-dark" style={{ float: 'left' }} onClick={this.handleImgPrev}>Prev</Button><Button variant="outline-dark" style={{ float: 'right' }} onClick={this.handleImgNext}>Next</Button>
          </Card.Body>
        </Card>
      );
    }
  }
  renderOverride(selectedActual) {
    if(selectedActual !== "") {
      return(
        <p><b>Override: {selectedActual}</b></p>
      );
    }
  }
  renderDetailCard(imglist, imgidx, selectedActual) {
    if(imglist.length > 0) {
      const imgobj = imglist[imgidx];
      return(
        <Card border="secondary" className="text-center">
          <Card.Header>Image: {imgobj.imgid}</Card.Header>
          <Card.Body>
            Prediction: {imgobj.prediction} (probability {parseFloat(imgobj.probability).toFixed(4)})
            {this.renderOverride(selectedActual)}
            <DropdownButton
            title="actuals"
            variant="outline-success"
            id="actuals"
            key="actuals"
          > 
          {['Center', 'Donut', 'Edge-Loc', 'Edge-Ring', 'Loc', 'Near-full', 'Random', 'Scratch', 'none'].map(
    variant => (
            <Dropdown.Item eventKey={variant} key={variant} onSelect={this.handleActualSelect}>{variant}</Dropdown.Item>
    ))}
          </DropdownButton>
          </Card.Body>
          <Card.Footer className="text-muted"><Button variant="success" onClick={this.handleActualSubmit}>Submit</Button></Card.Footer>
        </Card>
      );

    }
    
  }

  renderAll() {
   return (
    <Container>
    <Row style={{border: '1px solid grey'}}>
      <Col>
    <ButtonToolbar>
        <DropdownButton
          title="fabs"
          variant="outlne-primary"
          id="fabs"
          key="fabs"
        > 
        {this.renderFabList(this.state.fabs)}
        </DropdownButton>
        <DropdownButton
          title="cameras"
          variant="outlne-secondary"
          id="cameras"
          key="cameras"
        > 
        {this.renderCameraList(this.state.selectedFab)}
        </DropdownButton>
  </ButtonToolbar>
  </Col>
  <Col>
        From: <DatePicker selected={this.state.from_date} onChange={this.handleFromDate}/>
  </Col>
  <Col>
        To: <DatePicker selected={this.state.to_date} onChange={this.handleToDate}/>
  </Col>
    </Row>
    <Row>
      <Col>
        {this.renderImgCard(this.state.imglist, this.state.selectedImg, this.state.selectedFab, this.state.selectedCam)}
      </Col>
      <Col>
        {this.renderDetailCard(this.state.imglist, this.state.selectedImg, this.state.selectedActual)}
      </Col>
      <Col>
      <Card style={{ float: 'right' }} border="info" className="text-left">
        <Card.Header>Summary</Card.Header>
        <Card.Body>
          <Card.Text>
            Selected FAB: {this.state.selectedFab}
            <br></br>
            Selected Camera: {this.state.selectedCam}
            <br></br>
            Defect rate: {parseFloat(this.state.accuracy).toFixed(2)}%
          </Card.Text>
        </Card.Body>
      </Card>
      </Col>
    </Row>
  </Container>
   );
  }

  render() {
    return (
      <div className="Home">
        {this.props.isAuthenticated ? this.renderAll() : this.renderLander()}
      </div>
    );
  }
}
