package main

import (
	"fmt"

	"github.com/acme/shared-lib/client"
	metrics "github.com/acme/shared-lib/metrics"
	"github.com/pkg/errors"
)

func main() {
	fmt.Println("hi")
	_ = errors.New("x")
	_ = client.New()
	_ = metrics.New()
}
